CC := gcc
CC_FLAGS := -O0 -g -fPIC -Wall -Werror -march=native 

LIBINCLUDE := -Iinclude/ 

LD_FLAGS := -shared 

DEFAULT_FLAGS := -fPIC
TEST_FLAGS := -O0

MAINSRC := $(wildcard *.c)
MAINOBJ := $(patsubst %.c, %.o, $(MAINSRC))
MAIN := main

FUNCSRC := $(wildcard src/*.c)
FUNCOBJ := $(patsubst %.c, %.o, $(FUNCSRC))
FUNCLIB := libfunc.so

.PHONE: all clean

all: $(MAIN)

$(MAIN): $(MAINOBJ) $(FUNCLIB)
	$(CC) $(CC_FLAGS) $(LIBINCLUDE) -o $@ $< -ldl -lc -L. -lfunc

$(MAINOBJ): %.o:%.c
	$(CC) $(CC_FLAGS) $(LIBINCLUDE) $(DRIVERINCLUDE) -c $< -o $@

$(FUNCLIB): $(FUNCOBJ)
	$(CC) $(DEFAULT_FLAGS) $(LIBINCLUDE) $(TEST_FLAGS) $(LD_FLAGS) -o $@ $^

$(FUNCOBJ): %.o:%.c
	$(CC) $(DEFAULT_FLAGS) $(LIBINCLUDE) $(TEST_FLAGS) -c $< -o $@


clean: 
	@rm -f $(MAIN) $(MAINOBJ) $(FUNCLIB) $(FUNCOBJ) 
