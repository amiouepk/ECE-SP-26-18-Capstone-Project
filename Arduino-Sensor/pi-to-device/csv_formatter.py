import sys
import csv

DEFAULT = 4

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

def process_acceleration(accel_chunk):
    x_comp = accel_chunk[3:accel_chunk.find('|') - 1]
    y_comp = accel_chunk[accel_chunk.find('Y: ') + 3:accel_chunk.find('Z: ') - 3]
    z_comp = accel_chunk[accel_chunk.find('Z: ') + 3::]

    return [x_comp, y_comp, z_comp]

def process_gyro(gryo_chunk):
    gyro_x = gryo_chunk[8:gryo_chunk.find('|') - 1]
    gyro_y = gryo_chunk[gryo_chunk.find('gyro_y: ') + 8:gryo_chunk.find('gyro_z: ') - 3]
    gyro_z = gryo_chunk[gryo_chunk.find('gyro_z: ') + 8::]

    return [gyro_x, gyro_y, gyro_z]

def process_magnet(mag_chunk):
    mag_x = mag_chunk[7:mag_chunk.find('|') - 1]
    mag_y = mag_chunk[mag_chunk.find('mag_y: ') + 7:mag_chunk.find('mag_z') - 3]
    mag_z = mag_chunk[mag_chunk.find('mag_z') + 7::]

    return [mag_x, mag_y, mag_z]

def process_mpu(mpu_chunk):
    accel_data = process_acceleration(mpu_chunk[0])
    gyro_data = process_gyro(mpu_chunk[1])
    
    return accel_data, gyro_data

def process_bno(bno_chunk):

    #print(bno_chunk)
    accel_data = process_acceleration(bno_chunk[0])
    gyro_data = process_gyro(bno_chunk[1])
    #print(gyro_data)
    mag_data = process_magnet(bno_chunk[2])

    return accel_data, gyro_data, mag_data

def Mpu_data_reader(in_file, out_file):
    
    pass

def Bno_data_reader():
    pass

def Both_data_reader(chunk, extracted_vals):

    ev_len = len(extracted_vals)
    print(f"ev_len: {ev_len}")

    if ev_len != 40:
        sys.stderr.write("Wrong array length, Must be for Both")
        sys.exit(2)


    accel_data, gyro_data, mag_data = process_bno(chunk[2:5])

    i = 1
    j = 0

    while j < 3:
        
        #print(accel_data[j], gyro_data[j], mag_data[j])
        extracted_vals[i] = accel_data[j]
        extracted_vals[i + 3] = gyro_data[j]
        extracted_vals[i + 6] = mag_data[j]

        i += 1
        j += 1
    
    # print("extracted values")
    # for val in extracted_vals:
    #     print(val)

    i = 10
    j = 0
    accel_data = []
    gyro_data = []

    curr_accel_line = 6
    curr_gyro_line = 7

    #print(f"index 6: {chunk[6]}")
    #print(chun)

    print('new loop')
    while curr_gyro_line < len(chunk):
        #print(f"chunk len: {len(chunk)}")
        
        print(f"curr_gyro_line: {curr_gyro_line}")
        #print(f"length: {len(chunk[curr_accel_line:curr_gyro_line])}")
        #print(f"accel: {extracted_vals[curr_accel_line]}, gyro: {extracted_vals[curr_gyro_line]}")
        accel_data, gyro_data = process_mpu([chunk[curr_accel_line], chunk[curr_gyro_line]])
        #print(f"accel_data: {accel_data}, gyro_data: {gyro_data}")

        j = 0
        while j < 3:
            extracted_vals[i] = accel_data[j]
            extracted_vals[i + 3] = gyro_data[j]

            #print(f"i: {i}")
            print(f"extracted_vals[{i}]: {extracted_vals[i]}")
            print(f"extracted_vals[{i} + 3]: {extracted_vals[i + 3]}")

            j += 1
            i += 1
            
        i += 3
       
        curr_accel_line += 3
        curr_gyro_line += 3

        #i += 1


    #print(extracted_vals)
    
    return extracted_vals


    
    print("IN BOTH")


    return extracted_vals

def sensor_data_formatter():
    pass


def read_chunk(in_file):
    chunk = []

    for line in in_file:
        #print(f"line: {line}")
        #print(f"{i} % {num_lines} = {i % num_lines}")

        stripped = line.strip()
        if line.strip() == '':
            yield chunk
            chunk = []
        else:
            chunk.append(stripped)
        

    
def process_chunk(chunk, extracted_vals, mode):

    curr_time = chunk[0][7::]
    #print(f"curr_time: {curr_time}")
    extracted_vals[0] = curr_time

    if mode == 0:
        extracted_vals = Mpu_data_reader(chunk, extracted_vals)
    elif mode == 1:
        extracted_vals = Both_data_reader(chunk, extracted_vals)
    else:
        extracted_vals = bno_data_reader(chunk, extracted_vals)

    return extracted_vals

def live_writer():

    

    
    return

def file_io_manager(in_filename, out_filename, mode):

    if mode == 0:
        #num_lines = 17
        extracted_vals = [''] * 31
    elif mode == 1:
        #num_lines = 21
        extracted_vals = [''] * 40
    else:
        #num_lines = 26
        extracted_vals = [''] * 55
    

    try:
        with open(in_filename, "r", encoding="utf-8") as in_file:
            #convert_text_csv()
            with open("../../ML/ml-outputs/" + out_filename, "w+", newline='') as out_file:
                
                data_writer = csv.writer(out_file)
                
                
                i = 0

                for chunk in read_chunk(in_file):

                    #print(chunn)
                    extracted_vals = process_chunk(chunk, extracted_vals, mode)
                    data_writer.writerow(extracted_vals)
                    #print(extracted_vals)
                    


                
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

    if args_len == 3:
        if opt == 'live':
            live_writer(argv[2])

            sys.exit(0)
   

    if args_len >= 4:
        if opt == "mpu":
            sensor_option = 0 # MPU only input
        elif opt == "both":
            sensor_option = 1 # 1 BNO + remaining MPU
        elif opt == "bno":
            sensor_option = 2 # Only BNO 
    # elif args_len == 3:
    #     if opt == "live":
    #         sensor_option = 4

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

            file_io_manager(in_filename, out_filename, sensor_option)
                    
        # else:
        #     sys.stderr.write("You must have at least an input file (txt) with option for output file name")
        #     sys.exit(2)
    else:
        sys.stderr.write("Use -c or --convert option with input file (.txt)\n")
        sys.stderr.write("optional output file after intput file")
        sys.exit(2)

    #print("passed everything")
        

