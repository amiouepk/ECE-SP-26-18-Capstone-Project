
class mpuData:

    def __init__ (self, accel_x, accel_y, accel_z, roll, pitch, yaw):
        self.accel_x = accel_x
        self.accel_y = accel_y
        self.accel_z = accel_z
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw

    def print_data (self, num):
        all_data = ''
        all_data += f"Sensor {num + 1}: \n"
        all_data += f'X: {self.accel_x} | Y: {self.accel_y} | Z: {self.accel_z}\n'
        all_data += f'roll: {self.roll} | pitch: {self.pitch} | yaw: {self.yaw}\n'

        #print(all_data)
        # print(f"Sensor {num}: \n")
        # print(f'X: {self.accel_x} | Y: {self.accel_y} | Z: {self.accel_z}')
        # print(f'roll: {self.roll} | pitch: {self.pitch} | yaw: {self.yaw}')


        return all_data
        

