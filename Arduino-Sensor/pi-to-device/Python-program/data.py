
class mpuData:

    def __init__ (self, accel_x, accel_y, accel_z, roll, pitch, yaw):
        self.accel_x = accel_x
        self.accel_y = accel_y
        self.accel_z = accel_z
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw

    def print_data (self):
        print("Sensor Data:")
        print(f'X: {self.accel_x} | Y: {self.accel_y} | Z: {self.accel_z}')
        print(f'roll: {self.roll} | pitch: {self.pitch} | yaw: {self.yaw}')

