CC := gcc
CFLAGS := -O2 -Wall -Wextra -std=c11
LDFLAGS := -pthread

TARGET := bench_prio_call_overhead
SRC := bench_prio_call_overhead.c

.PHONY: all clean run

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

run: $(TARGET)
	sudo ./$(TARGET)

clean:
	rm -f $(TARGET)
