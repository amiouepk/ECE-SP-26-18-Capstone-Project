import sys
import pandas as pd

window_size = None
in_file = None
out_file = 'window_output.csv'
seekback_len = 0
out_msg = ''
avg_arr = None
var_arr = None


def mean_calc(in_arr):
    global avg_arr
    avg_arr = [0] * 54  

    i = 0
    while i < len(in_arr):
        j = 1
        #print(len(in_arr[i]))
        while j < len(in_arr[i]) - 1:
            #print(j)
            avg_arr[j - 1] += float(in_arr[i][j])

            j += 1
        i += 1
    
    for avg in avg_arr:
        avg = avg / window_size

    return avg_arr
    



    pass

def variance_calc(in_arr):
    global avg_arr, var_arr
    num_rows = len(in_arr)
    if num_rows == 0:
        return [0.0] * len(avg_arr)

    num_cols = len(avg_arr)
    sum_sq_diff = [0.0] * num_cols

    for row in in_arr:
        for i in range(1, len(row) - 1):
            col_idx = i - 1
            if col_idx >= num_cols:
                break
            try:
                val = float(row[i])
            except (ValueError, IndexError):
                val = 0.0   
            diff = val - avg_arr[col_idx]
            sum_sq_diff[col_idx] += diff * diff

    var_arr = [ssd / num_rows for ssd in sum_sq_diff]
    return var_arr

def window_indexer(in_fd, out_fd):
    #print ('here')
    global seekback_len, out_msg
    in_arr = []
    out_msg = ''


    curr_line = in_fd.readline().decode('utf-8')
    if not curr_line:
        return False
    #print(curr_line)
    out_msg += curr_line
    in_arr.append(curr_line.split(','))
    
    seekback_len += len(curr_line)

    i = 1
    
    while i < window_size:

        curr_line = in_fd.readline().decode('utf-8')
        if not curr_line:
            return False    
        out_msg += curr_line
        in_arr.append(curr_line.split(','))
        
        i += 1

    mean_calc(in_arr)
    
    variance_calc(in_arr)
    
    # print(f'{in_arr}\n')
    # print(f'{avg_arr}\n')
    # print(f'{var_arr}\n')

    return True
        
    
        

    


if __name__ == '__main__':

    arg_len = len(sys.argv)
    
    if arg_len != 4:
        print('follow this format: window_data.py in_file out_file window_size')
        sys.exit(2)
    
    in_file = sys.argv[1] + '.csv'
    out_file = sys.argv[2] + '.csv'
    window_size = int(sys.argv[3])

    #df = pd.DataFrame()
    

    try:
        with open(in_file, 'rb') as in_fd:
            print(f"Seekable: {in_fd.seekable()}")
            seekback_len += len(in_fd.readline().decode('utf-8'))
            #print(f'First seekback len: {seekback_len}')
            #print(in_fd.readline())
            with open(out_file, 'w+') as out_fd:
                # window_indexer(in_fd, out_fd)
                # print(f'Second seekback len: {seekback_len}')
                # in_fd.seek (seekback_len, 0)
                # window_indexer(in_fd, out_fd)
                while True:
                    
                    if not window_indexer(in_fd, out_fd):
                        break
                    in_fd.seek(seekback_len, 0)
                    out_fd.write(f'{avg_arr}, {var_arr}\n')
                    
               
    except FileNotFoundError:
        sys.stderr.write(f'input file {in_file} not found')
        sys.exit(2)
    
    
