from __future__ import annotations 

"""Tk GUI（Call the legacy pipeline to generate a numbered thread-call graph）。

Button：
- Load C: use gcc to generate the expand file and copy it to `test/<basename>/`
- Load expand: only update the expand path
- generate dag graph：call `python -m mycallypro <expand>` produce DOT, then render it to PNG with `dot`

Note: to support direct execution inside the package directory, this module includes fallback imports and working-directory handling.
"""

import shutil 
import subprocess 
import sys 
import tempfile 
from pathlib import Path 
from typing import Optional 

import tkinter as tk 
from tkinter import filedialog ,messagebox 

# config_files directory：<repo>/intermediate_results/<base>/config_files/
PROJECT_ROOT =Path (__file__ ).resolve ().parent .parent 

# Import fallback for direct execution outside the package (`python3 gui.py`)
try :# Recommended: python3 -m <package>.ui.generation_gui
    from ..generation .builder import build_callee_info 
    from ..generation .model import CallGraph ,RenderOptions 
    from ..generation .parser import Parser 
    from ..generation .renderer import DotRenderer 
    from ..generation .threads import infer_thread_edges 
    from ..runtime_env import module_cmd ,module_env 
except Exception :# absolute import fallback (execute python3 gui.py in projectroot directory)
    pkg_root =Path (__file__ ).resolve ().parent .parent 
    sys .path .insert (0 ,str (pkg_root .parent ))
    try :
        import importlib 

        pkg =importlib .import_module (pkg_root .name )
        build_callee_info =importlib .import_module (f"{pkg.__name__}.generation.builder").build_callee_info 
        model_mod =importlib .import_module (f"{pkg.__name__}.generation.model")
        CallGraph =model_mod .CallGraph 
        RenderOptions =model_mod .RenderOptions 
        Parser =importlib .import_module (f"{pkg.__name__}.generation.parser").Parser 
        DotRenderer =importlib .import_module (f"{pkg.__name__}.generation.renderer").DotRenderer 
        infer_thread_edges =importlib .import_module (f"{pkg.__name__}.generation.threads").infer_thread_edges 
        runtime_mod =importlib .import_module (f"{pkg.__name__}.runtime_env")
        module_cmd =runtime_mod .module_cmd 
        module_env =runtime_mod .module_env 
    except Exception :
        sys .path .insert (0 ,str (pkg_root /"generation"))
        from builder import build_callee_info # type: ignore
        from model import CallGraph ,RenderOptions # type: ignore
        from parser import Parser # type: ignore
        from renderer import DotRenderer # type: ignore
        from threads import infer_thread_edges # type: ignore
        module_cmd =None # type: ignore
        module_env =None # type: ignore


def _module_command (relative_module :str )->list [str ]:
    if module_cmd is not None :
        return module_cmd (relative_module ,python_executable =sys .executable )
    return [sys .executable ,"-m",f"{PROJECT_ROOT.name}.{relative_module}"]


def _module_environment ():
    return module_env ()if module_env is not None else None 


class MyCallyGUI :
    def __init__ (self ,root :tk .Tk )->None :
        self .root =root 
        self .root .title ("MyCally Assistant")
        self .root .geometry ("1200x800")

        self .current_c_path :Optional [Path ]=None 
        self .current_expand_path :Optional [Path ]=None 
        self .current_image :Optional [tk .PhotoImage ]=None 

        self ._build_ui ()

        # ------------------------------------------------------------------ UI --

    def _build_ui (self )->None :
        main =tk .Frame (self .root ,bg ="#ECEFF1")
        main .pack (fill =tk .BOTH ,expand =True )

        # Left button area
        sidebar =tk .Frame (main ,width =220 ,bg ="#CFD8DC")
        sidebar .pack (side =tk .LEFT ,fill =tk .Y )

        def add_button (text :str ,command )->None :
            btn =tk .Button (
            sidebar ,
            text =text ,
            command =command ,
            width =20 ,
            height =2 ,
            bg ="#ECEFF1",
            activebackground ="#B0BEC5",
            relief =tk .RAISED ,
            font =("Microsoft YaHei",10 ),
            )
            btn .pack (pady =12 ,padx =12 )

        add_button ("Load C file",self .load_c_file )
        add_button ("Load expand file",self .load_expand_file )
        add_button ("generate dag graph",self .generate_dag )
        add_button ("View conditional nodes",self .generate_conditions_dag )
        add_button ("generateconfig_files",self .generate_config_files )

        # redundancy-handling mode options
        mode_frame =tk .LabelFrame (
        sidebar ,
        text ="redundancy handling mode",
        bg ="#CFD8DC",
        font =("Microsoft YaHei",9 ,"bold"),
        padx =8 ,
        pady =8 
        )
        mode_frame .pack (pady =12 ,padx =12 ,fill =tk .X )

        self .smart_mode =tk .BooleanVar (value =False )
        self .clean_mode =tk .BooleanVar (value =False )

        smart_check =tk .Checkbutton (
        mode_frame ,
        text ="smart detection (--smart)",
        variable =self .smart_mode ,
        bg ="#CFD8DC",
        font =("Microsoft YaHei",9 ),
        command =self ._on_mode_change 
        )
        smart_check .pack (anchor =tk .W ,pady =2 )

        clean_check =tk .Checkbutton (
        mode_frame ,
        text ="clean rebuild (--clean)",
        variable =self .clean_mode ,
        bg ="#CFD8DC",
        font =("Microsoft YaHei",9 ),
        command =self ._on_mode_change 
        )
        clean_check .pack (anchor =tk .W ,pady =2 )

        mode_help =tk .Label (
        mode_frame ,
        text ="default: overwrite existingFile\nSmart: skip unchanged files\nclean up: delete and then generate again",
        bg ="#CFD8DC",
        font =("Consolas",8 ),
        fg ="#546E7A",
        justify =tk .LEFT 
        )
        mode_help .pack (anchor =tk .W ,pady =(6 ,0 ))

        # Right display area
        content =tk .Frame (main ,bg ="#FFFFFF")
        content .pack (side =tk .RIGHT ,fill =tk .BOTH ,expand =True )

        info_frame =tk .Frame (content ,bg ="#FFFFFF")
        info_frame .pack (fill =tk .X ,padx =12 ,pady =12 )

        self .c_label =tk .Label (info_frame ,text ="C File: <Not selected>",anchor ="w",bg ="#FFFFFF",font =("Consolas",11 ))
        self .c_label .pack (fill =tk .X )

        self .expand_label =tk .Label (info_frame ,text ="expand File: <Not selected>",anchor ="w",bg ="#FFFFFF",font =("Consolas",11 ))
        self .expand_label .pack (fill =tk .X ,pady =(6 ,0 ))

        canvas_frame =tk .Frame (content ,bg ="#ECEFF1")
        canvas_frame .pack (fill =tk .BOTH ,expand =True ,padx =12 ,pady =12 )

        self .canvas =tk .Canvas (canvas_frame ,bg ="#FAFAFA",relief =tk .SUNKEN )
        self .canvas .pack (fill =tk .BOTH ,expand =True )
        self .canvas .create_text (
        0 ,
        0 ,
        text ="The generated DAG graph will be displayed here",
        anchor =tk .NW ,
        font =("Microsoft YaHei",12 ),
        fill ="#607D8B",
        tags ="placeholder",
        )

        self .canvas .bind ("<ButtonPress-1>",self ._start_pan )
        self .canvas .bind ("<B1-Motion>",self ._do_pan )
        self .canvas .bind ("<MouseWheel>",self ._on_zoom )
        self .canvas .bind ("<Button-4>",self ._on_zoom )# Linux scroll up
        self .canvas .bind ("<Button-5>",self ._on_zoom )# Linux scroll down
        self .canvas_scale =1.0 

        # -------------------------------------------------------------- Helpers --

    def _on_mode_change (self )->None :
        """Ensure `smart` and `clean` cannot be selected at the same time when the mode checkbox changes"""
        if self .smart_mode .get ()and self .clean_mode .get ():
        # If both are selected, clear the previously selected one
        # Simplified handling: `clean` takes priority
            self .smart_mode .set (False )

    def load_c_file (self )->None :
        path =filedialog .askopenfilename (title ="Select C Source File",filetypes =[("C File","*.c"),("All files","*")])
        if not path :
            return 

        c_path =Path (path ).resolve ()
        if not c_path .exists ():
            messagebox .showerror ("Error","The selected C file does not exist.")
            return 

        try :
            expand_path =self ._compile_to_expand (c_path )
        except Exception as exc :
            messagebox .showerror ("compilefailed",str (exc ))
            return 

        base_name =c_path .stem 
        target_dir =(Path (__file__ ).parent /"test"/base_name ).resolve ()
        target_dir .mkdir (parents =True ,exist_ok =True )

        dest_expand =(target_dir /expand_path .name ).resolve ()
        try :
            shutil .copy2 (expand_path ,dest_expand )
        except Exception as exc :
            messagebox .showerror ("Copy failed",f"Unable to copy the expand file to {dest_expand}。\n{exc}")
            return 

        self .current_c_path =c_path 
        self .current_expand_path =dest_expand 

        self ._update_labels ()
        self ._clear_canvas ()

        messagebox .showinfo ("Completed",f"Generated expand File：\n{dest_expand}")

    def load_expand_file (self )->None :
        path =filedialog .askopenfilename (
        title ="Select expand File",filetypes =[("expand File","*.expand"),("All files","*")]
        )
        if not path :
            return 

        expand_path =Path (path ).resolve ()
        if not expand_path .exists ():
            messagebox .showerror ("Error","The selected expand file does not exist.")
            return 

        self .current_c_path =None 
        self .current_expand_path =expand_path .resolve ()

        self ._update_labels ()
        self ._clear_canvas ()

    def generate_dag (self )->None :
        if not self .current_expand_path or not self .current_expand_path .exists ():
            messagebox .showwarning ("Info","PleaseSelect expand File。")
            return 

        try :
            dot_str ,png_path =self ._build_dag (self .current_expand_path ,threads_only =True )
        except Exception as exc :
            messagebox .showerror ("Generation failed",str (exc ))
            return 

        try :
            self ._show_image (png_path )
        except Exception as exc :
            messagebox .showerror ("Display failed",f"Generatedimage, but error occurred when loading:\n{exc}")
            return 

        messagebox .showinfo ("Completed",f"Generatedthread graph DAG graph:\n{png_path}")

    def generate_conditions_dag (self )->None :
        if not self .current_expand_path or not self .current_expand_path .exists ():
            messagebox .showwarning ("Info","PleaseSelect expand File。")
            return 

        try :
            dot_str ,png_path =self ._build_conditions_dag (self .current_expand_path )
        except Exception as exc :
            messagebox .showerror ("Generation failed",str (exc ))
            return 

        try :
            self ._show_image (png_path )
        except Exception as exc :
            messagebox .showerror ("Display failed",f"Generatedimage, but error occurred when loading:\n{exc}")
            return 

        messagebox .showinfo ("Completed",f"Generatedfull view graph DAG graph:\n{png_path}")

    def generate_config_files (self )->None :
        """One-click generation of all config files: DAG graph, conditional-node graph, and circle.txt"""
        if not self .current_expand_path or not self .current_expand_path .exists ():
            messagebox .showwarning ("Info","PleaseSelect expand File。")
            return 

        try :
        # Determine the output directories（three-stage layout + flat structure）
            base_name =self ._derive_base_name (self .current_expand_path )

            # Stage 3 - config_files directory（new location: `intermediate_results/<base>/config_files`）
            config_base =PROJECT_ROOT /"intermediate_results"/base_name /"config_files"
            config_base .mkdir (parents =True ,exist_ok =True )

            # Stage 2 - intermediate_results directory（temporary files created during processing）
            intermediate_base =PROJECT_ROOT /"intermediate_results"/base_name 
            intermediate_base .mkdir (parents =True ,exist_ok =True )

            # Create intermediate_results subdirectories
            (intermediate_base /"debug").mkdir (exist_ok =True )
            (intermediate_base /"temp").mkdir (exist_ok =True )
            (intermediate_base /"images").mkdir (exist_ok =True )
            (intermediate_base /"logs").mkdir (exist_ok =True )

            generated_files =[]

            # 0. Copy the source file and expand file to the config_files root directory（flat structure）
            messagebox .showinfo ("Progress","Copying the source file...")
            import shutil 

            # Copy the expand file to the root directory
            expand_dest =config_base /self .current_expand_path .name 
            shutil .copy2 (self .current_expand_path ,expand_dest )
            generated_files .append (f"✓ {self.current_expand_path.name}")

            # Copy the source file to the root directory(if it exists)
            if self .current_c_path and self .current_c_path .exists ():
                source_dest =config_base /self .current_c_path .name 
                shutil .copy2 (self .current_c_path ,source_dest )
                generated_files .append (f"✓ {self.current_c_path.name}")

                # 1. dag_generation（threads-only）
            messagebox .showinfo ("Progress","Generating the DAG graph (thread view)...")
            dot_str_threads ,png_threads =self ._build_dag_to_config (
            self .current_expand_path ,
            config_base ,
            intermediate_base ,
            threads_only =True 
            )
            generated_files .append (f"✓ {base_name}.dot")

            # 2. Generate the conditional-node graph (full version)
            messagebox .showinfo ("Progress","Generating the conditional-node graph (full view)...")
            dot_str_full ,png_full =self ._build_dag_to_config (
            self .current_expand_path ,
            config_base ,
            intermediate_base ,
            threads_only =False 
            )
            generated_files .append (f"✓ {base_name}_full.dot")

            # 3. Generated `circle.txt`
            messagebox .showinfo ("Progress","Generating circle.txt config files...")
            txt_path =self ._generate_circle_txt (self .current_expand_path ,config_base )
            if txt_path .exists ():
                generated_files .append (f"✓ circle.txt")

                # PNG images are generated in the intermediate_results directory
            generated_files .append (f"✓ Images generated in the intermediate_results directory")

            # Display the last generated image (full view)
            try :
                self ._show_image (png_full )
            except Exception :
                pass 

                # Display the success message
            files_list ="\n".join (generated_files )
            messagebox .showinfo (
            "generateCompleted",
            f"allconfig_filesGenerated! \n\nconfig_files directory:\n{config_base}\n\ngenerate File:\n{files_list}"
            )

        except Exception as exc :
            messagebox .showerror ("Generation failed",f"Error generatingconfig_files:\n{exc}")
            import traceback 
            traceback .print_exc ()

            # ------------------------------------------------------------- Internal --

    def _compile_to_expand (self ,c_path :Path )->Path :
        """Call gcc to generate the expand file and return its path."""
        work_dir =c_path .parent 
        base_name =c_path .name 

        with tempfile .NamedTemporaryFile (dir =work_dir ,suffix =".o",delete =False )as tmp :
            obj_name =Path (tmp .name ).name 
        try :
            subprocess .run (
            ["gcc","-fdump-rtl-expand","-c",base_name ,"-o",obj_name ],
            cwd =work_dir ,
            check =True ,
            stdout =subprocess .PIPE ,
            stderr =subprocess .PIPE ,
            )
        except subprocess .CalledProcessError as exc :
            raise RuntimeError (exc .stderr .decode ("utf-8",errors ="ignore")or str (exc ))
        finally :
            obj_file =work_dir /obj_name 
            if obj_file .exists ():
                obj_file .unlink ()

        candidates =sorted (work_dir .glob (f"{base_name}.*.expand"),key =lambda p :p .stat ().st_mtime ,reverse =True )
        if not candidates :
            raise RuntimeError ("No expand file generated by gcc was found.")
        return candidates [0 ]

    def _build_dag (self ,expand_path :Path ,threads_only :bool =False )->tuple [str ,Path ]:
        """parse expand File and generate DAG PNG (use the legacy pipeline to preserve numbering and thread semantics)."""
        # By running the package module, directly reuse the legacy numbering and thread-edge patching logic
        try :
            import subprocess 
            cmd =_module_command ("generation.legacy")
            if threads_only :
                cmd .append ("--threads-only")
            cmd .append (str (expand_path .resolve ()))
            # The working directory should be the project root directory (the parent directory of mycallyplus)
            work_dir =PROJECT_ROOT .parent 
            proc =subprocess .run (
            cmd ,
            check =True ,
            stdout =subprocess .PIPE ,
            stderr =subprocess .PIPE ,
            cwd =str (work_dir ),
            env =_module_environment (),
            )
            dot_str =proc .stdout .decode ("utf-8",errors ="ignore")
        except subprocess .CalledProcessError as exc :
        # Capture detailed errors for failed command execution
            error_msg =exc .stderr .decode ("utf-8",errors ="ignore")if exc .stderr else str (exc )
            raise RuntimeError (f"generate DOT failed：\n{error_msg}")
        except Exception as exc :
            raise RuntimeError (f"generate DOT failed：{exc}")

        base_name =self ._derive_base_name (expand_path )
        target_dir =(Path (__file__ ).parent /"test"/base_name ).resolve ()
        target_dir .mkdir (parents =True ,exist_ok =True )

        dot_path =(target_dir /"dag.dot").resolve ()
        png_path =(target_dir /"dag.png").resolve ()
        dot_path .write_text (dot_str ,encoding ="utf-8")

        try :
            subprocess .run (["dot","-Tpng",str (dot_path ),"-o",str (png_path )],check =True )
        except FileNotFoundError as exc :
            raise RuntimeError ("The `dot` command was not found. Please install Graphviz.")from exc 
        except subprocess .CalledProcessError as exc :
            raise RuntimeError (exc .stderr .decode ("utf-8",errors ="ignore")or "dot command execution failed。")from exc 

        return dot_str ,png_path 

    def _build_conditions_dag (self ,expand_path :Path )->tuple [str ,Path ]:
        """parse expand File and Generate the full-view DAG PNG, including thread edges and conditional nodes."""
        try :
            import subprocess 
            cmd =_module_command ("generation.legacy")+[str (expand_path .resolve ())]
            work_dir =PROJECT_ROOT .parent 
            proc =subprocess .run (
            cmd ,
            check =True ,
            stdout =subprocess .PIPE ,
            stderr =subprocess .PIPE ,
            cwd =str (work_dir ),
            env =_module_environment (),
            )
            dot_str =proc .stdout .decode ("utf-8",errors ="ignore")
        except subprocess .CalledProcessError as exc :
            error_msg =exc .stderr .decode ("utf-8",errors ="ignore")if exc .stderr else str (exc )
            raise RuntimeError (f"Failed to generate the full-view DOT：\n{error_msg}")
        except Exception as exc :
            raise RuntimeError (f"Failed to generate the full-view DOT：{exc}")

        base_name =self ._derive_base_name (expand_path )
        target_dir =(Path (__file__ ).parent /"test"/base_name ).resolve ()
        target_dir .mkdir (parents =True ,exist_ok =True )

        dot_path =(target_dir /"dag_full.dot").resolve ()
        png_path =(target_dir /"dag_full.png").resolve ()
        dot_path .write_text (dot_str ,encoding ="utf-8")

        try :
            subprocess .run (["dot","-Tpng",str (dot_path ),"-o",str (png_path )],check =True )
        except FileNotFoundError as exc :
            raise RuntimeError ("The `dot` command was not found. Please install Graphviz.")from exc 
        except subprocess .CalledProcessError as exc :
            raise RuntimeError (exc .stderr .decode ("utf-8",errors ="ignore")or "dot command execution failed。")from exc 

        return dot_str ,png_path 

    def _build_dag_to_config (self ,expand_path :Path ,config_dir :Path ,intermediate_dir :Path ,threads_only :bool =False )->tuple [str ,Path ]:
        """Generate the DAG and save it to the config_files directory (flat structure) and the intermediate_results directory"""
        try :
            import subprocess 
            cmd =_module_command ("generation.legacy")
            if threads_only :
                cmd .append ("--threads-only")
            cmd .append (str (expand_path .resolve ()))
            work_dir =PROJECT_ROOT .parent 
            proc =subprocess .run (
            cmd ,
            check =True ,
            stdout =subprocess .PIPE ,
            stderr =subprocess .PIPE ,
            cwd =str (work_dir ),
            env =_module_environment (),
            )
            dot_str =proc .stdout .decode ("utf-8",errors ="ignore")
        except subprocess .CalledProcessError as exc :
            error_msg =exc .stderr .decode ("utf-8",errors ="ignore")if exc .stderr else str (exc )
            raise RuntimeError (f"generate DOT failed：\n{error_msg}")
        except Exception as exc :
            raise RuntimeError (f"generate DOT failed：{exc}")

            # Get the base filename
        base_name =expand_path .stem 
        if base_name .endswith ('.233r'):
            base_name =base_name [:-5 ]
        elif '.'in base_name :
            base_name =base_name .split ('.')[0 ]

            # Save the DOT file to the config_files root directory（flat structure; see `test/config_files/`）
        if threads_only :
            dot_path =config_dir /f"{base_name}.dot"
        else :
            dot_path =config_dir /f"{base_name}_full.dot"

        dot_path .write_text (dot_str ,encoding ="utf-8")

        # Save the PNG images to the intermediate_results directory（not part of dag_describe config files）
        images_dir =intermediate_dir /"images"
        images_dir .mkdir (parents =True ,exist_ok =True )

        if threads_only :
            png_path =images_dir /f"{base_name}.png"
        else :
            png_path =images_dir /f"{base_name}_full.png"

        try :
            subprocess .run (["dot","-Tpng",str (dot_path ),"-o",str (png_path )],check =True )
        except FileNotFoundError as exc :
            raise RuntimeError ("The `dot` command was not found. Please install Graphviz.")from exc 
        except subprocess .CalledProcessError as exc :
            raise RuntimeError (exc .stderr .decode ("utf-8",errors ="ignore")or "dot command execution failed。")from exc 

        return dot_str ,png_path 

    def _generate_circle_txt (self ,expand_path :Path ,config_dir :Path )->Path :
        """Generated `circle.txt`config_files"""
        try :
            import subprocess 

            txt_path =config_dir /"circle.txt"

            cmd =[
            *_module_command ("generation.legacy"),
            str (expand_path .resolve ()),
            "--export-txt",str (txt_path ),
            "--output-base",str (PROJECT_ROOT )
            ]

            # Add redundancy-handling mode arguments
            if self .smart_mode .get ():
                cmd .append ("--smart")
            if self .clean_mode .get ():
                cmd .append ("--clean")

            work_dir =PROJECT_ROOT .parent 
            proc =subprocess .run (
            cmd ,
            check =True ,
            stdout =subprocess .PIPE ,
            stderr =subprocess .PIPE ,
            cwd =str (work_dir ),
            env =_module_environment (),
            )

            return txt_path 

        except subprocess .CalledProcessError as exc :
            error_msg =exc .stderr .decode ("utf-8",errors ="ignore")if exc .stderr else str (exc )
            raise RuntimeError (f"generate circle.txt failed：\n{error_msg}")
        except Exception as exc :
            raise RuntimeError (f"generate circle.txt failed：{exc}")

    def _derive_base_name (self ,expand_path :Path )->str :
        name =expand_path .name 
        if ".c"in name :
            return name .split (".c",1 )[0 ]
        return expand_path .stem 

    def _update_labels (self )->None :
        c_text =f"C File：{self.current_c_path}"if self .current_c_path else "C File: <Not selected>"
        expand_text =f"expand File：{self.current_expand_path}"if self .current_expand_path else "expand File: <Not selected>"
        self .c_label .config (text =c_text )
        self .expand_label .config (text =expand_text )

    def _clear_canvas (self )->None :
        self .canvas .delete ("all")
        self .current_image =None 
        self .canvas_scale =1.0 
        self .canvas .create_text (
        0 ,
        0 ,
        text ="The generated DAG graph will be displayed here",
        anchor =tk .NW ,
        font =("Microsoft YaHei",12 ),
        fill ="#607D8B",
        tags ="placeholder",
        )

    def _show_image (self ,image_path :Path )->None :
        self .canvas .delete ("all")
        try :
            self .current_image =tk .PhotoImage (file =str (image_path ))
        except Exception :
        # Pillow Fallback for environments where `PhotoImage` does not support PNG
            try :
                from PIL import Image ,ImageTk # type: ignore

                img =Image .open (str (image_path ))
                self .current_image =ImageTk .PhotoImage (img )
            except Exception as exc :# final failure
                raise RuntimeError (f"Unable to load the image：{exc}")
        self .canvas .create_image (0 ,0 ,anchor =tk .NW ,image =self .current_image ,tags ="image")
        self .canvas .config (scrollregion =self .canvas .bbox (tk .ALL ))

    def _start_pan (self ,event )->None :
        self .canvas .scan_mark (event .x ,event .y )

    def _do_pan (self ,event )->None :
        self .canvas .scan_dragto (event .x ,event .y ,gain =1 )

    def _on_zoom (self ,event )->None :
        if self .current_image is None :
            return 
        if event .type ==tk .EventType .ButtonPress and event .num not in (4 ,5 ):
            return 

        if event .type ==tk .EventType .MouseWheel :
            delta =event .delta 
        else :# Linux scroll (Button-4/5)
            delta =120 if event .num ==4 else -120 

        scale_factor =1.1 if delta >0 else 0.9 
        self .canvas_scale *=scale_factor 
        self .canvas .scale ("all",event .x ,event .y ,scale_factor ,scale_factor )
        self .canvas .config (scrollregion =self .canvas .bbox (tk .ALL ))


def main ()->None :
    try :
        root =tk .Tk ()
    except tk .TclError as exc :
        raise RuntimeError (
        "Unable to start graph interface: No available displayservice was detected."
        "\nPlease run it in the environment that supports GUI, or set the DISPLAY variable."
        )from exc 
    app =MyCallyGUI (root )
    root .mainloop ()


if __name__ =="__main__":
    main ()
