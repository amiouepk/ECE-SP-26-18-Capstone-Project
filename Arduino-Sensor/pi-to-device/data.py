
class mpuData:

    def __init__ (self, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z):
        self.accel_x = accel_x
        self.accel_y = accel_y
        self.accel_z = accel_z
        self.gyro_x = gyro_x
        self.gyro_y = gyro_y
        self.gyro_z = gyro_z

    def print_data (self, num):
        all_data = ''
        all_data += f"Sensor {num + 1}: \n"
        all_data += f'X: {self.accel_x} | Y: {self.accel_y} | Z: {self.accel_z}\n'
        all_data += f'gyro_x: {self.gyro_x} | gyro_y: {self.gyro_y} | gyro_z: {self.gyro_z}\n'

        #print(all_data)
        # print(f"Sensor {num}: \n")
        # print(f'X: {self.accel_x} | Y: {self.accel_y} | Z: {self.accel_z}')
        # print(f'gyro_x: {self.gyro_x} | gyro_y: {self.gyro_y} | gyro_z: {self.gyro_z}')


        return all_data

class bnoData:
    def __init__ (self, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, mag_x, mag_y, mag_z):
        self.accel_x = accel_x
        self.accel_y = accel_y
        self.accel_z = accel_z
        self.gyro_x = gyro_x
        self.gyro_y = gyro_y
        self.gyro_z = gyro_z
        self.mag_x = mag_x
        self.mag_y = mag_y
        self.mag_z = mag_z

    def print_data (self, num):
        all_data = ''
        all_data += f"Sensor {num + 1}: \n"
        all_data += f'X: {self.accel_x} | Y: {self.accel_y} | Z: {self.accel_z}\n'
        all_data += f'gyro_x: {self.gyro_x} | gyro_y: {self.gyro_y} | gyro_z: {self.gyro_z}\n'
        all_data += f'mag_x: {self.mag_x} | mag_y: {self.mag_y} | mag_z: {self.mag_z}\n'

        return all_data

        #print(all_data)
        # print(f"Sensor {num}: \n")
        # print(f'X: {self.accel_x} | Y: {self.accel_y} | Z: {self.accel_z}')
        # print(f'gyro_x: {self.gyro_x} | gyro_y: {self.gyro_y} | gyro_z: {self.gyro_z}')

# class mpu:
#     self.init