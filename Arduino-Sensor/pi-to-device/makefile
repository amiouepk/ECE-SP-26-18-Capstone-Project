CC = gcc
CFLAGS = -g -Wall -Wextra -fsanitize=address
TARGET = input-processor 
# SRCS = 

all:
	$(CC) $(CFLAGS) main.c -o $(TARGET)

clean:
	rm -f $(TARGET)

recomp: clean all
