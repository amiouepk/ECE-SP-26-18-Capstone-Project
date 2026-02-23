#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>

#define BUFFER_SIZE 64

/*
 * Need to:
 * - Connect websocket jag did in python
 * - ML model :()
 * 
 *
 */


int sample_text();



int main(int argc, char **argv){

    char text[] = "text";

    printf("%d\n", argc);

    if (!(argc - 1)){ //for direct from pi to model via websocket
        printf("not ready yet\n");
    }
    else if (!strcmp(text, argv[1])){
        printf("here\n");
        sample_text();
    }
    else {
        printf("Try:\nno option: for websocket\ntext: for sample text\n");
    }

    return 0;
}

/*
Using foepn, fread, ... cuz its more portable, while open, read, ... are posix specific. Also it
more frankly easier to do. less things to keep track of
ALso, efficiency gains from effectivley using systemcalls are not very significant because this will
be runnng on a device like a computer, not a microcontroller of some sort.
*/
int sample_text(){

    FILE *in_fp = fopen("sample-input.txt", "r");
    if (in_fp == NULL){
        perror("input file fopen error");
        exit(EXIT_FAILURE);
    }

    FILE *out_fp = fopen("formated-output.txt", "w+");
    if (out_fp == NULL){
        perror("output file fopen error");
        exit(EXIT_FAILURE);
    }

    char in_buff[BUFFER_SIZE]; // Input Buffer
    char out_buff[BUFFER_SIZE]; // Output Buffer

    int bytes_read; // Number of bytes read by fread (used for error checking)

    int loop_break = 0; // Loop break to break from nested loop
    int start; // used for the for fseek
    int read_num = 0; // number of times read to get to beginning of data

    int num_buff[5]; // Temporary buffer used before turning string into float/double

    while (1){
        bytes_read = fread(in_buff, 1, BUFFER_SIZE - 1, in_fp);
        if (ferror(in_fp)){
            fprintf(stderr, "fread error when seeking for start\n");
            exit(EXIT_FAILURE);
        }
        else if (feof(in_fp)){
            fprintf(stderr, "Read Error: reached end of file when seeking for start of data.\n");
            exit(EXIT_FAILURE);
        }

       //printf("bytes_read: %d\n", bytes_read);

      
        in_buff[bytes_read] = '\0';
        
        printf("\nread number: %d\n", read_num++);
        printf("%s", in_buff);

        for (int i = 0; i < 64; i++){
            if (in_buff[i] == '|'){
                loop_break = 1;
                start = i + 3; 
                printf("\nstart: %d\n", start);
                
                break;
            }

        }

        if (loop_break){
            break;
        }
        //start += 64;
    }

    int fseek_num = fseek(in_fp, -(BUFFER_SIZE - 1 - start), SEEK_CUR);
    if (fseek_num){
        perror("fseek error when navigating to start of file");
        exit(EXIT_FAILURE);
    }

    /* now what i have to do:
     * 1. Read the number till the /
     * 2. convert the number to a double/float
     * 3. Put in an array/struct to be used easily
     */ 

    while (1) {
        bytes_read = fread(in_buff, 1, BUFFER_SIZE - 1, in_fp);
        if (ferror(in_fp)){
                fprintf(stderr, "fread error when seeking for start\n");
                exit(EXIT_FAILURE);
        }
        else if (feof(in_fp)){
            fprintf(stderr, "Read Error: reached end of file when seeking for start of data.\n");
            exit(EXIT_FAILURE);
        } 



    }

    //printf("\nafter fseek: %s\n", in_buff);
    
    
    

    
    


    






    return 0;
}


