import sys
import csv

def help():
    print("Options: ")
    print("-h, --help       Prints help text")
    print("mpu              Converts Earlier MPU only Data")
    print("                 to CSV file format")
    print("both             Converts Earlier Single BNO and")
    print("                 MPU only Data to CSV file format")
    print("bno              Converts New BNO only data to")
    print("                 CSV file format")
    print("-c, --convert    need name of input file (txt)")
    print("                 option for output file name")

def convert_text_csv():
    print("in convert_text_csv function")

def mpu_convert_to_csv():
    print("In mpu csv convet function")
    pass

def Mpu_data_reader(in_file, out_file):
    
    pass

def bno_data_reader():
    pass

def Bno_data_reader():
    pass

def Both_data_reader(data_chunk, extracted_vals):
    print("IN BOTH")
    pass

def sensor_data_formatter():
    pass


def File_io_manager(in_filename, out_filename, mode):

    
    if mode == 0:
        num_lines = 17
        extracted_vals = [''] * 31
    elif mode == 1:
        num_lines = 21
        extracted_vals = [''] * 40
    else:
        num_lines = 26
        extracted_vals = [''] * 55

    

    try:
        with open(in_filename, "r", encoding="utf-8") as in_file:
            #convert_text_csv()
            with open("../../ML/ml-outputs/" + out_filename, "w+", newline='') as out_file:
                
                csv.writer(out_file)
                
                curr_time = None
                mod_val = num_lines + 1
                
                data_chunk = [''] * num_lines
                

                for i, line in enumerate(in_file):
                    #print(f"line: {line}")
                    print(f"{i} % {num_lines}")
                    if i % mod_val == num_lines:
                        
                        curr_time = data_chunk[0][7:data_chunk[0].find('ms')]
                        print(f"curr_time: {curr_time}")
                        extracted_vals[0] = curr_time


                        if mode == 0:
                            Mpu_data_reader(curr_time, data_chunk)
                            
                        elif mode == 1:
                            Both_data_reader(data_chunk, extracted_vals)
                        else:
                            bno_data_reader(data_chunk, extracted_vals)

                        data_chunk = [''] * num_lines
                        continue

                    
                    data_chunk[i % num_lines] = line.strip()


                
                


                
                #convert_text_csv()
    except FileNotFoundError:
        sys.stderr.write("This File does not exist. Enter A file that does exist")
        sys.exit(2)


#def main 

#__all__ = 

if __name__ == "__main__":
    
    args_len = len(sys.argv)

    if args_len < 2:
        sys.stderr.write("enter a valid option")
        help()
        sys.exit(2)

    opt = sys.argv[1]
    #print(f"opt: {opt}")
    
    out_filename = "output.csv"
    in_filename = None
    sensor_option = 3 # MPU input, BNO + MPU input, or only BNO input option
    tstr_min_len = 3

    if opt == "-h" or opt == "--help":
        help()
        exit(0)

    if args_len >= 4:
        if opt == "mpu":
            sensor_option = 0 # MPU only input
        elif opt == "both":
            sensor_option = 1 # 1 BNO + remaining MPU
        elif opt == "bno":
            sensor_option = 2 # Only BNO            

    if sensor_option != 3:
        opt = sys.argv[2]
        tstr_min_len = 4

    if opt == "-c" or opt == "--convert":
        if args_len > tstr_min_len:
            in_filename = sys.argv[tstr_min_len - 1]
            print(f"in_filename: {in_filename}")

            if not in_filename.endswith(".txt"):
                sys.stderr.write('Input file name must end with ".txt"')
                sys.exit(2)

            if args_len == tstr_min_len + 1:
                out_filename = sys.argv[tstr_min_len] + '.csv'

            File_io_manager(in_filename, out_filename, sensor_option)
                    
        # else:
        #     sys.stderr.write("You must have at least an input file (txt) with option for output file name")
        #     sys.exit(2)
    else:
        sys.stderr.write("Use -c or --convert option with input file (.txt)\n")
        sys.stderr.write("optional output file after intput file")
        sys.exit(2)

    #print("passed everything")
        

