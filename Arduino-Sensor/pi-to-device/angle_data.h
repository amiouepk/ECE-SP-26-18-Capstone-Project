#ifndef ANGLE_DATA_H
#define ANGLE_DATA_H

#define FILENAME_SIZE 1024
#define BUFFSIZE 128

void startHelpFunction();

void numPrintMessage();

//void clearBuffer();

int oldintParseConvert(char* int_buff);

int intParseConvert(char* input_buffer, int input_buffer_length);

void oldstrParse(char* buff, int numchar);

void strParse(char* input_buffer, int input_buffer_length);





#endif