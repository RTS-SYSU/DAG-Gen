# -*- coding: utf-8 -*-
"""
Exporter module
Used to export mycallypro parse results into various formats, including the `circle.txt` format
"""

from __future__ import annotations 

import re 
from pathlib import Path 
from typing import Dict ,List ,Optional ,Tuple 

from .model import CallGraph 


def write_dot (path :Path ,dot_str :str )->None :
    """writeDOT File"""
    path .parent .mkdir (parents =True ,exist_ok =True )
    path .write_text (dot_str ,encoding ="utf-8")


def write_circle_auto (graph :CallGraph ,path :Path )->None :
    """automaticGenerate `circle.txt` from the call graph (simplified version, kept backward compatible)"""
    path .parent .mkdir (parents =True ,exist_ok =True )
    content :List [str ]=[]
    content .append ("mutex")
    mutex_entries =_collect_mutex_entries (graph )
    content .extend (mutex_entries or [""])
    content .append ("")
    content .append ("semaphore")
    sem_entries =_collect_semaphore_entries (graph )
    content .extend (sem_entries or [""])
    path .write_text ("\n".join (content ),encoding ="utf-8")


def _collect_mutex_entries (graph :CallGraph )->List [str ]:
    idx =1 
    entries :List [str ]=[]
    stack :List [Tuple [str ,str ]]=[]
    for func in sorted (graph .functions ):
        seq =graph .functions [func ].call_sequence 
        for call in seq :
            if "pthread_mutex_lock"in call :
                stack .append ((func ,f"MUTEX_{idx}"))
            elif "pthread_mutex_unlock"in call and stack :
                lock_func ,var =stack .pop ()
                entries .append (f"{lock_func} {var} {idx}")
                idx +=1 
    return entries 


def _collect_semaphore_entries (graph :CallGraph )->List [str ]:
    idx =1 
    posts :List [Tuple [str ,str ]]=[]
    entries :List [str ]=[]
    for func in sorted (graph .functions ):
        seq =graph .functions [func ].call_sequence 
        for call in seq :
            if "sem_post"in call :
                posts .append ((func ,f"SEM_{idx}"))
            elif "sem_wait"in call and posts :
                post_func ,var =posts .pop (0 )
                entries .append (f"{post_func} {var} {idx}")
                idx +=1 
    return entries 


    # ============================================================================
    # Legacy-format exporter (used to export from the `functions` dictionary in `legacy.py`)
    # ============================================================================

class CircleTxtExporter :
    """Export config files in `circle.txt` format for `dag_describe`"""

    def __init__ (self ,functions :Dict ,expand_file :Path ,source_file :Optional [Path ]=None ):
        self .functions =functions 
        self .expand_file =expand_file 
        self .source_file =source_file 

        # Used to generate unique IDs
        self ._id_counters :Dict [str ,int ]={}

        # Store extracted records
        self .mutex_records :List [Dict ]=[]
        self .sem_records :List [Dict ]=[]

    def export (self ,output_path :Path )->None :
        """Export to the specified path"""
        # 1. Extract mutex and semaphore information
        self ._extract_sync_primitives ()

        # 2. Generate the TXT file content
        content =self ._generate_txt_content ()

        # 3. writeFile
        output_path .parent .mkdir (parents =True ,exist_ok =True )
        output_path .write_text (content ,encoding ='utf-8')

    def _extract_sync_primitives (self )->None :
        """Extract mutex and semaphore information from the functioncall list"""
        for func_name ,func_data in self .functions .items ():
            mycalls =func_data .get ('mycalls',[])

            # Maintain an API-call counter for each function
            api_counters ={}

            for idx ,call_node in enumerate (mycalls ):
            # Parse the node name
                node_info =self ._parse_node_name (call_node )
                if not node_info :
                    continue 

                api_name =node_info ['api']

                # Determine whether it is a mutex or semaphore API
                if self ._is_mutex_api (api_name ):
                # Count which invocation of this API it is within the function
                    api_key =f"{func_name}_{api_name}"
                    call_count =api_counters .get (api_key ,0 )
                    api_counters [api_key ]=call_count +1 

                    record =self ._extract_mutex_record (
                    call_node ,node_info ,func_name ,call_count 
                    )
                    if record :
                        self .mutex_records .append (record )

                elif self ._is_sem_api (api_name ):
                # Count which invocation of this API it is within the function
                    api_key =f"{func_name}_{api_name}"
                    call_count =api_counters .get (api_key ,0 )
                    api_counters [api_key ]=call_count +1 

                    record =self ._extract_sem_record (
                    call_node ,node_info ,func_name ,call_count 
                    )
                    if record :
                        self .sem_records .append (record )

    def _parse_node_name (self ,node_name :str )->Optional [Dict ]:
        """
        Parse the node name
        format: "main/while/pthread_mutex_lock5"
        Returns: {
            'full': 'main/while/pthread_mutex_lock5',
            'prefix': 'main/while',
            'api': 'pthread_mutex_lock',
            'seq': 5
        }
        """
        if not node_name :
            return None 

            # Extract the index
        match =re .search (r'(\d+)$',node_name )
        if not match :
            return None 

        seq_num =int (match .group (1 ))
        api_with_seq =node_name .split ('/')[-1 ]
        api_name =api_with_seq [:-len (match .group (1 ))]

        # Extract the prefix
        parts =node_name .rsplit ('/',1 )
        prefix =parts [0 ]if len (parts )>1 else ''

        return {
        'full':node_name ,
        'prefix':prefix ,
        'api':api_name ,
        'seq':seq_num 
        }

    def _is_mutex_api (self ,api_name :str )->bool :
        """Determine whether it is a mutex API"""
        return 'pthread_mutex_lock'in api_name or 'pthread_mutex_unlock'in api_name 

    def _is_sem_api (self ,api_name :str )->bool :
        """Determine whether it is a semaphore API"""
        return 'sem_post'in api_name or 'sem_wait'in api_name 

    def _extract_mutex_record (
    self ,
    call_node :str ,
    node_info :Dict ,
    func_name :str ,
    call_index :int 
    )->Optional [Dict ]:
        """Extract mutex records"""
        api_name =node_info ['api']

        # Extract source-code location
        line_num ,file_name =self ._extract_source_location (
        func_name ,api_name ,call_index 
        )

        # Extract the variable name (try to obtain it from the expand file)
        var_name =self ._extract_variable_name (func_name ,api_name ,call_index )
        if not var_name :
            var_name ='mutex'# default value

            # generate unique ID
        idx_name =self ._generate_unique_id (var_name ,'mutex')

        return {
        'node':call_node ,
        'type':'mutex',
        'var':var_name ,
        'idx':idx_name ,
        'line':line_num ,
        'file':file_name ,
        'api':api_name 
        }

    def _extract_sem_record (
    self ,
    call_node :str ,
    node_info :Dict ,
    func_name :str ,
    call_index :int 
    )->Optional [Dict ]:
        """Extract semaphore records"""
        api_name =node_info ['api']

        # Extract source-code location
        line_num ,file_name =self ._extract_source_location (
        func_name ,api_name ,call_index 
        )

        # Prefer extracting the semaphore name from source-code call arguments; use expand `symbol_ref` only as a fallback.
        var_name =self ._extract_source_arg_name (api_name ,line_num )
        if not var_name :
            var_name =self ._extract_variable_name (func_name ,api_name ,call_index )
        if not var_name :
            var_name ='sem'# default value

            # generate unique ID
        idx_name =self ._generate_unique_id (var_name ,'sem')

        return {
        'node':call_node ,
        'type':'sem',
        'var':var_name ,
        'idx':idx_name ,
        'line':line_num ,
        'file':file_name ,
        'api':api_name 
        }

    def _extract_source_location (
    self ,
    func_name :str ,
    api_name :str ,
    call_index :int 
    )->Tuple [Optional [int ],Optional [str ]]:
        """\nExtract source-code location information from expandFile\n        RTLformatExamples:\n        (call_insn 42 41 43 (call (mem:QI (symbol_ref:DI (\"pthread_mutex_lock\")) \n            [0  S1 A8]) (const_int 0 [0])) \"simpletest.c\":31:5 -1\n        """
        if not self .expand_file .exists ():
            return None ,None 

        try :
            content =self .expand_file .read_text (encoding ='utf-8',errors ='ignore')
            lines =content .splitlines ()

            # Build multiple regex patterns and try to match different formats
            escaped_api =re .escape (api_name )

            # Pattern 1: full match where `symbol_ref` and source-code location are on the same or nearby lines
            pattern1 =re .compile (
            rf'symbol_ref.*?"{escaped_api}".*?"([^"]+)":(\d+)',
            re .IGNORECASE 
            )
            # Pattern 2: `call_insn` may be followed by a source-code location
            pattern2 =re .compile (r'"([^"]+\.c)":(\d+)(?::(\d+))?')

            matches =[]
            in_function =False 
            current_location =None 

            for i ,line in enumerate (lines ):
            # Detect function boundaries
                if f';; Function {func_name}'in line :
                    in_function =True 
                    current_location =None 
                    continue 
                elif line .startswith (';; Function ')and in_function :
                    break 

                if in_function :
                # Find lines containing the API name
                    if escaped_api in line and 'symbol_ref'in line :
                    # Check whether the current line contains source-code location information
                        loc_match =pattern2 .search (line )
                        if loc_match :
                            matches .append ((int (loc_match .group (2 )),loc_match .group (1 )))
                        else :
                        # Search nearby lines for location information
                            found =False 
                            # Search forward first
                            for j in range (i +1 ,min (i +5 ,len (lines ))):
                                loc_match =pattern2 .search (lines [j ])
                                if loc_match :
                                    matches .append ((int (loc_match .group (2 )),loc_match .group (1 )))
                                    found =True 
                                    break 
                                    # Then search backward
                            if not found :
                                for j in range (max (0 ,i -5 ),i ):
                                    loc_match =pattern2 .search (lines [j ])
                                    if loc_match :
                                        matches .append ((int (loc_match .group (2 )),loc_match .group (1 )))
                                        break 

                                        # Return the corresponding match based on `call_index`
            if matches and call_index <len (matches ):
                line_num ,file_name =matches [call_index ]
                return line_num ,file_name 

        except Exception as e :
        # Debug: print exception information
            import sys 
            print (f"Debug: Failed to extract location for {func_name}/{api_name}[{call_index}]: {e}",file =sys .stderr )

        return None ,None 

    def _extract_variable_name (
    self ,
    func_name :str ,
    api_name :str ,
    call_index :int 
    )->Optional [str ]:
        """
        Try to extract the variable name from the expand file
        """
        if not self .expand_file .exists ():
            return None 

        try :
            content =self .expand_file .read_text (encoding ='utf-8',errors ='ignore')
            lines =content .splitlines ()

            in_function =False 
            api_count =0 

            for i ,line in enumerate (lines ):
                if f';; Function {func_name}'in line :
                    in_function =True 
                    continue 
                elif line .startswith (';; Function ')and in_function :
                    break 

                if in_function and api_name in line :
                    if api_count ==call_index :
                    # Search upward for nearby `symbol_ref` entries (possibly variables)
                        for j in range (max (0 ,i -10 ),i ):
                            var_match =re .search (r'\(symbol_ref[^"]*"([^"]+)"\)',lines [j ])
                            if var_match :
                                var_candidate =var_match .group (1 )
                                # Filter out obvious function symbol names and keep variable names (for example `sem_01` / `mutex_01`)
                                if var_candidate .startswith ("pthread_"):
                                    continue 
                                    # Some toolchains may emit the callee name as a symbol_ref too.
                                if var_candidate in {"sem_post","sem_wait","sem_init","sem_destroy"}:
                                    continue 
                                return var_candidate 
                        break 
                    api_count +=1 

        except Exception :
            pass 

        return None 

    def _extract_source_arg_name (self ,api_name :str ,line_num :Optional [int ])->Optional [str ]:
        """Extract synchronization-primitive variable names from source-code call arguments, e.g. `sem_post(&sem_01) -> sem_01`."""
        if not self .source_file or line_num is None :
            return None 
        if not self .source_file .exists ():
            return None 

        try :
            source_lines =self .source_file .read_text (encoding ="utf-8",errors ="ignore").splitlines ()
            if line_num <1 or line_num >len (source_lines ):
                return None 
            line =source_lines [line_num -1 ]
            m =re .search (rf"\b{re.escape(api_name)}\s*\(\s*&?\s*([A-Za-z_]\w*)",line )
            if m :
                return m .group (1 )
        except Exception :
            pass 

        return None 

    def _generate_unique_id (self ,var_name :str ,category :str )->str :
        """Generate a unique ID for the variable"""
        key =f"{category}_{var_name}"
        if key not in self ._id_counters :
            self ._id_counters [key ]=len ([k for k in self ._id_counters if k .startswith (category )])+1 
        return f"{var_name}{self._id_counters[key]}"

    def _generate_txt_content (self )->str :
        """Generate the TXT file content"""
        lines =[]

        # mutex part
        if self .mutex_records :
            lines .append ("mutex")
            for record in self .mutex_records :
                line_parts =[
                record ['node'],
                record ['type'],
                record ['idx']
                ]
                if record ['line']is not None :
                    line_parts .append (str (record ['line']))
                if record ['file']is not None :
                    line_parts .append (record ['file'])

                lines .append (' '.join (line_parts ))
            lines .append ("")
            lines .append ("")

            # semaphore part
        if self .sem_records :
            lines .append ("semaphore")
            for record in self .sem_records :
                line_parts =[
                record ['node'],
                record ['type'],
                record ['idx']
                ]
                if record ['line']is not None :
                    line_parts .append (str (record ['line']))
                if record ['file']is not None :
                    line_parts .append (record ['file'])

                lines .append (' '.join (line_parts ))
            lines .append ("")
            lines .append ("")
            lines .append ("")

        return '\n'.join (lines )


def export_circle_txt (
functions :Dict ,
expand_file :Path ,
output_path :Path ,
source_file :Optional [Path ]=None 
)->None :
    """
    Convenience function: export config files in `circle.txt` format
    
    Args:
        functions: mycallyproparsefunction dictionary
        expand_file: GCC RTL expandFilepath
        output_path: outputtxtFilepath
        source_file: source-code file path (optional)
    """
    exporter =CircleTxtExporter (functions ,expand_file ,source_file )
    exporter .export (output_path )
