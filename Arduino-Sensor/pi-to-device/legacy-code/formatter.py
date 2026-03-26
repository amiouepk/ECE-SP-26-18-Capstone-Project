import sys
import numpy as np
import data 


def bosch_reading():

    pass


def file_reading(msg):
    print(msg)
    imu_num = 6
    
    #bno_sensor_num 
    sensor_num = [None] * imu_num
    

    if not msg:
        print("Message was empty")
        return

    curr_num_arr = np.empty(6)
    bno_curr_num_arr = np.empty(9)
    curr_str_num = '' 

    line_data = None
    
    i = 0
    j = 2
    k = 0

    if (msg[0] != 'B'):
        return
    else:
        while (msg[j] != '|'):
            if (msg[j] == '/'):
                #print(f"STR: {curr_str_num}")
                bno_curr_num_arr[k] = float(curr_str_num)
                curr_str_num = ''
                j += 1
                k += 1
                continue
        
            #print(f"J VAL: {msg[j]}")

            curr_str_num += msg[j]

            j += 1
        
        bno_curr_num_arr[k] = float(curr_str_num)
        curr_str_num = ''
        line_data = data.bnoData(bno_curr_num_arr[0], bno_curr_num_arr[1], bno_curr_num_arr[2], bno_curr_num_arr[3], bno_curr_num_arr[4], bno_curr_num_arr[5], bno_curr_num_arr[6], bno_curr_num_arr[7], bno_curr_num_arr[8])

        #print(f'line_data: {line_data.accel_x}')

        for num in bno_curr_num_arr:
            print(f'num: {num}')

        sensor_num[i] = line_data

        bno_data = sensor_num[i].print_data(i)

        print(f'bno data: {bno_data}')

        i += 1
        j += 1
        k = 0

        #bno_data = sen


        
    

    while (i < imu_num):
        #print(f'j: {j}, msg[j]: {msg[j]}')

        if (msg[j] == '|'): 

            curr_num_arr[k] = float(curr_str_num)
            curr_str_num = ''
            line_data = data.mpuData(curr_num_arr[0], curr_num_arr[1], curr_num_arr[2], curr_num_arr[3], curr_num_arr[4], curr_num_arr[5])

            sensor_num[i] = line_data

            i += 1
            j += 1
            k = 0
            
            continue
        

        if (msg[j] == '/'):
            #print(f"STR: {curr_str_num}")

            curr_num_arr[k] = float(curr_str_num)
            curr_str_num = ''
            j += 1
            k += 1
            continue
        
        #print(f"J VAL: {msg[j]}")

        curr_str_num += msg[j]

        j += 1

        #while (j < 7):



    i = 0
    all_data = ''

    while (i < imu_num):
        #print(f'sensor_num[{i}].print_data({i}): {sensor_num[i].print_data(i)}')
        all_data += sensor_num[i].print_data(i)
        #sensor_num[i].print_data(i)
        i += 1


    #print(all_data)
    
    #line_data.print_data()   


    return all_data



def sample_input(path):
    
    num_sensors = 6

    out_file = open('sensor_data.txt', 'w+')

    try: 
        with open(path, "r", encoding="utf-8") as file:
            
            for line in file:
                # print("in line loop")
                data = file_reading(line.strip())
                
                if data is not None:
                    out_file.write(data + '\n')
                
            
    except FileNotFoundError: 
        print('Please enter a valid file path')
    except Exception as e:
        print(f"An error has occured: {e}")
    


if __name__ == "__main__":

    if (len(sys.argv) > 1):

        sample_input(sys.argv[1])
        

    
    print("finished")
