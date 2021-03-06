import pycom
import time
import utime
import machine
from machine import Pin
from machine import I2C
from machine import Timer
from micropython import const
from machine import PWM
import mpu6050
import sys
import VL53L0X
import _thread
from tmp102 import _tmp102
import math
import MPU6050 as mpu6050
import Position
import Network
from machine import PWM
from machine import ADC

# Setting Constants for Serial Busses
I2C_BUS_0 = const(0)
I2C_BUS_1 = const(1)
LIDAR_DEFAULT_ADDR = const(0x29)
LIDAR_ADDR_REGISTER = const(0x8A)
LIDAR1_ADDR = const(0x15)
LIDAR2_ADDR = const(0x16)
LIDAR3_ADDR = const(0x17)
LIDAR4_ADDR = const(0x18)
TEMP_ADDR = const(0x48)

# self, error_prior=0, integral=0, KP=3, KI=5, KD=0.01, bias=0,
#                          iteration_time=0.05, error=20, tol=1,
# Constants for PID controller
KP = (0.6, 1.5)
KI = (0.2, 0)
KD = (0.04, 0)
bias = (0, 0)
iteration_time = (0.5, 1)
V = 40.1
W = 200.934


# Class for movement and Sensing of Robot
class SwarmBody():
    # Init function initialising pins and sensors
    def __init__(self, motor1F='P11', motor1B='P12', motor2F='P21',
                 motor2B='P20',
                 SDA='P9',
                 SCL='P10',
                 lidar_DIO1='P2', lidar_DIO2='P3', lidar_DIO3='P4', lidar_DIO4='P5'):
        self.initialise_gyro()
        self.initialise_rest(SDA, SCL, lidar_DIO1, lidar_DIO2, lidar_DIO3, lidar_DIO4)
        self.initialise_motor(motor1F, motor1B, motor2F, motor2B)

        self.gyro_data = 0
        self.robot_move_flag = 0
        self.x = 0
        self.y = 0
        self.l1 = 0
        self.l2 = 0
        self.l3 = 0
        self.l4 = 0
        self.temp = 0
        self.battery = 0
        self._get_pos = 0
        self.Arrival_Flag = False
        self.l_limit = 10;
        self.Collision_Chain_Num = 0;
        self.Col_Reverse_Time = 1;
        self.S_adc = ADC(bits = 12)
        self.S_apin = self.S_adc.channel(pin = 'P15',attn = self.S_adc.ATTN_11DB)

    def initialise_rest(self, SDA, SCL, lidar_DIO1, lidar_DIO2, lidar_DIO3, lidar_DIO4):
        _thread.start_new_thread(self._initialise_rest, (SDA, SCL, lidar_DIO1, lidar_DIO2, lidar_DIO3, lidar_DIO4))

    def _initialise_rest(self, SDA, SCL, lidar_DIO1, lidar_DIO2, lidar_DIO3, lidar_DIO4):
        self.initialise_I2C(SDA, SCL)
        self.initialise_lidar(SDA, SCL, lidar_DIO1, lidar_DIO2, lidar_DIO3, lidar_DIO4)
        self.initialise_temp()

    def initialise_gyro(self):
        try:
            _thread.start_new_thread(self.initialise_gyro_new, (1, 1))
        except IOError:
            self.initialise_gyro()

    def initialise_solar_panel_monitor(self, solar_panel_AD):
        self.solar_panel_AD = solar_panel_AD
        self.solar_panel_adc = machine.ADC()
        self.solar_panel_APIN = self.solar_panel_adc.channel(pin=self.solar_panel_AD)

    def initialise_I2C(self, SDA, SCL, baudrate=9600):
        self.baudrate = baudrate
        self.SDA = SDA
        self.SCL = SCL
        self.I2C = I2C(2)
        self.I2C.init(I2C.MASTER, baudrate=self.baudrate, pins=(self.SDA, self.SCL))

    # TODO: Battery Monitor code
    # Function for initialising all pin functionality for lidar
    def set_lidar(self, lidar_DIO1, lidar_DIO2, lidar_DIO3, lidar_DIO4):
        try:
            self._set_lidar(ID=1, lidar_DIO=lidar_DIO1)
            self._set_lidar(ID=2, lidar_DIO=lidar_DIO2)
            self._set_lidar(ID=3, lidar_DIO=lidar_DIO3)
            self._set_lidar(ID=4, lidar_DIO=lidar_DIO4)
        except OSError:

            self.set_lidar(lidar_DIO1, lidar_DIO2, lidar_DIO3, lidar_DIO4)

    def initialise_lidar(self, SDA, SCL, lidar_DIO1, lidar_DIO2, lidar_DIO3, lidar_DIO4):

        self.lidar_DIO1 = Pin(lidar_DIO1, mode=Pin.OUT)
        self.lidar_DIO2 = Pin(lidar_DIO2, mode=Pin.OUT)
        self.lidar_DIO3 = Pin(lidar_DIO3, mode=Pin.OUT)
        self.lidar_DIO4 = Pin(lidar_DIO4, mode=Pin.OUT)
        self.lidar_DIO1.value(0)
        self.lidar_DIO2.value(0)
        self.lidar_DIO3.value(0)
        self.lidar_DIO4.value(0)
        self.set_lidar(lidar_DIO1, lidar_DIO2, lidar_DIO3, lidar_DIO4)
        self._get_pos = 1
        # while True:
        # self.l1, self.l2, self.l3, self.l4 = self.get_lidar()

    def _set_lidar(self, ID, lidar_DIO):
        if ID == 1:
            self.lidar_DIO1.value(0)
            self.lidar_DIO1 = Pin(lidar_DIO, mode=Pin.IN)
            self.write_address(LIDAR1_ADDR)
            self.tof1 = VL53L0X.VL53L0X(i2c=self.I2C, address=LIDAR1_ADDR)
            self.tof1.set_Vcsel_pulse_period(self.tof1.vcsel_period_type[0], 18)
            self.tof1.set_Vcsel_pulse_period(self.tof1.vcsel_period_type[1], 14)
            device = self.I2C.scan()
            print(device)
        elif ID == 2:
            self.lidar_DIO2.value(0)
            self.lidar_DIO2 = Pin(lidar_DIO, mode=Pin.IN)
            self.write_address(LIDAR2_ADDR)
            self.tof2 = VL53L0X.VL53L0X(i2c=self.I2C, address=LIDAR2_ADDR)
            self.tof2.set_Vcsel_pulse_period(self.tof2.vcsel_period_type[0], 18)
            self.tof2.set_Vcsel_pulse_period(self.tof2.vcsel_period_type[1], 14)
            device = self.I2C.scan()
            print(device)
        elif ID == 3:
            self.lidar_DIO3.value(0)
            self.lidar_DIO3 = Pin(lidar_DIO, mode=Pin.IN)
            self.write_address(LIDAR3_ADDR)
            self.tof3 = VL53L0X.VL53L0X(i2c=self.I2C, address=LIDAR3_ADDR)
            self.tof3.set_Vcsel_pulse_period(self.tof3.vcsel_period_type[0], 18)
            self.tof3.set_Vcsel_pulse_period(self.tof3.vcsel_period_type[1], 14)
            device = self.I2C.scan()
            print(device)

        elif ID == 4:
            self.lidar_DIO4.value(0)
            self.lidar_DIO4 = Pin(lidar_DIO, mode=Pin.IN)
            self.write_address(LIDAR4_ADDR)
            self.tof4 = VL53L0X.VL53L0X(i2c=self.I2C, address=LIDAR4_ADDR)
            self.tof4.set_Vcsel_pulse_period(self.tof4.vcsel_period_type[0], 18)
            self.tof4.set_Vcsel_pulse_period(self.tof4.vcsel_period_type[1], 14)
            device = self.I2C.scan()
            print(device)

    def write_address(self, new_addr):
        self.I2C.writeto_mem(LIDAR_DEFAULT_ADDR, LIDAR_ADDR_REGISTER, new_addr & 0x7F)

    # Function for initialising all pin functionality for the motor driver
    def initialise_motor(self, motor1F, motor1B, motor2F, motor2B):
        self.motor1F = Pin(motor1F, mode=Pin.OUT)
        self.motor1B = Pin(motor1B, mode=Pin.OUT)
        self.motor2F = Pin(motor2F, mode=Pin.OUT)
        self.motor2B = Pin(motor2B, mode=Pin.OUT)
        self.motor_PWM = PWM(0, frequency=500)
        self.pwm1 = "P6"
        self.pwm2 = "P7"
        self.duty_cycle = 0.5
        self.w = 200.934
        self.v = 0.401
        self.chrono = Timer.Chrono()
        self.motor_stop()

    # Function for initialising all pin functionality for the gyro

    def initialise_gyro_new(self, x, y):
        mpu = mpu6050.MPU6050()
        mpu.dmpInitialize()
        mpu.setDMPEnabled(True)

        # get expected DMP packet size for later comparison
        packetSize = mpu.dmpGetFIFOPacketSize()

        i = 0  # iteration count
        sum_yaw = 0  # summing totals to calculate the mean
        current_yaw = 0
        print('\n'"Calculating zero-offset.")
        print("Please Stand By...")
        while True:

            fifoCount = mpu.getFIFOCount()      #
            while fifoCount < packetSize:       # major oscillations without this
                fifoCount = mpu.getFIFOCount()  #

            result = mpu.getFIFOBytes(packetSize)
            q = mpu.dmpGetQuaternion(result)
            g = mpu.dmpGetGravity(q)
            ypr = mpu.dmpGetYawPitchRoll(q, g)
            yaw = (ypr['yaw'] * 180 / math.pi)

            if i < 750:
                i+=1

            if i <= 600:  # skip the first 600 iterations to give it a chance to settle/stop drifting
                pass

            if i > 600 and i <= 700:  # take the average of the next 100 iterations after that (where it has settled to when stationary)
                sum_yaw += yaw
                if i == 700:
                    avg_yaw = (sum_yaw / 100)  # avg_yaw = the zero error

                    if avg_yaw > 0:
                        print('\n'"ALERT !!!")
                        print("Average yaw is positive.")
                        print("If not working check this first !")

                    else:
                        pass


            if i > 700:

                current_yaw = yaw - avg_yaw  # ===  [ robot can only start moving at this point ] === #

                if avg_yaw < 0:              # New code starts here.

                    if current_yaw > 180:
                        current_yaw = current_yaw - 180
                        current_yaw = -180 + current_yaw
                    else:
                        pass

                elif avg_yaw > 0:
                    if current_yaw < -180:
                        current_yaw =  current_yaw + 180
                        current_yaw = 180 - current_yaw
                    else:
                        pass

                self.gyro_data = current_yaw

            fifoCount -= packetSize
            mpu.resetFIFO()

    # Function for initialising pin functionality for the temperature sensor
    def initialise_temp(self):
        self.temp_sensor = _tmp102.Tmp102(self.I2C, TEMP_ADDR)

    def move_to(self, x, y, org, ang_org):
        COMM = (float(x), float(y))
        route = Position.best_route(COMM, org, ang_org)
        ang_org = route[2]
        self.rotational_movement(route[0], 0.3)
        self.linear_movement(route[1], 0.3)

    def rotational_movement(self, rot_mov, w):
        t_rot = rot_mov[1] / w
        if rot_mov[0] == 1:
            self.rotate_clockwise()
        elif rot_mov[0] == 0:
            self.rotate_anti_clockwise()
        while (self.chrono.read() < t_rot):
            pass
        self.motor_stop()
        self.chrono.stop()

    def linear_movement(self, lin_mov, v):
        t_lin = lin_mov[1] / v
        if lin_mov[0] == 1:
            self.move_forward()
        elif lin_mov[0] == 0:
            self.move_backward()
        while self.chrono.read() < t_lin:
            pass
        self.motor_stop()
        self.chrono.stop()

    def motor_stop(self):
        Pin(self.motor1F, mode=Pin.OUT).value(0)  # Pin1
        Pin(self.motor1B, mode=Pin.OUT).value(0)  # Pin2
        Pin(self.motor2F, mode=Pin.OUT).value(0)  # Pin3
        Pin(self.motor2B, mode=Pin.OUT).value(0)  # Pin4
        Pin(self.pwm1, mode=Pin.OUT).value(0)
        Pin(self.pwm2, mode=Pin.OUT).value(0)

    # Function to commands motor driver forwards, taking in a speed and distance
    def move_forward(self):
        self.chrono.start()
        self.motor1F.value(1)
        self.motor2F.value(1)
        self.motor_PWM.channel(0, pin=self.pwm1, duty_cycle=self.duty_cycle)
        self.motor_PWM.channel(0, pin=self.pwm2, duty_cycle=self.duty_cycle)
        #print("hello")

        return

    # Function to command motor driver backwards, taking in a speed and distance
    def move_backward(self):
        self.chrono.start()
        self.motor1B.value(1)
        self.motor2B.value(1)
        self.motor_PWM.channel(0, pin=self.pwm1, duty_cycle=self.duty_cycle)
        self.motor_PWM.channel(0, pin=self.pwm2, duty_cycle=self.duty_cycle)

        return

    # Function to rotate clockwise, taking in an angle and a rotational speed
    def rotate_clockwise(self):
        self.chrono.start()
        self.motor1B.value(1)
        self.motor2F.value(1)
        self.motor1F.value(0)
        self.motor2B.value(0)
        self.motor_PWM.channel(0, pin=self.pwm1, duty_cycle=self.duty_cycle)
        self.motor_PWM.channel(0, pin=self.pwm2, duty_cycle=self.duty_cycle)

        return

    # Function to rotate anti-clockwise, taking in an angle and a rotational speed
    def rotate_anti_clockwise(self):
        self.chrono.start()
        self.motor1F.value(1)
        self.motor2B.value(1)
        self.motor1B.value(0)
        self.motor2F.value(0)
        self.motor_PWM.channel(0, pin=self.pwm1, duty_cycle=self.duty_cycle)
        self.motor_PWM.channel(0, pin=self.pwm2, duty_cycle=self.duty_cycle)

        return

    # Function to get lidar readings [TBC]
    def get_lidar(self):
        # print("[+] getting lidar")
        self.tof1.start()
        self.tof2.start()
        self.tof3.start()
        self.tof4.start()
        data_tof1 = self.tof1.read()
        data_tof2 = self.tof2.read()
        data_tof3 = self.tof3.read()
        data_tof4 = self.tof4.read()
        data_tof1 /= 10
        data_tof2 /= 10
        data_tof3 /= 10
        data_tof4 /= 10
        return data_tof1, data_tof2, data_tof3, data_tof4  # in cm

    # Function to get solar panel voltage throughout the voltage divider
    def get_solar_panel_vol(self):
        vol = self.solar_panel_APIN.value()
        return vol

    # TODO: Write angle calculation function
    def _alarm_get_angle(self, alarm):
        self.get_angle()

    def get_angle(self):
        # get analog read of gyro minus the zero voltage point
        # Divide this by the gyro sensitivity
        # Add this to the current angle, keep track of global current angle

        fifoCount = self.mpu.getFIFOCount()  #
        while fifoCount < self.packetSize:  # major oscillations without this
            fifoCount = self.mpu.getFIFOCount()  #

        result = self.mpu.getFIFOBytes(self.packetSize)
        q = self.mpu.dmpGetQuaternion(result)
        g = self.mpu.dmpGetGravity(q)
        ypr = self.mpu.dmpGetYawPitchRoll(q, g)
        yaw = ypr['yaw'] * 180 / math.pi

        current_yaw = yaw - self.avg_yaw  # ===  [ robot can only start moving at this point ] === #
        self.robot_move_flag = 1
        print(current_yaw)
        self.gyro_data = current_yaw
        return current_yaw

    # Function to get temperature readings
    def get_temp(self):
        temp = self.temp_sensor.temperature
        self.temp = temp
        print("[+] Temp Reading: ", temp)
        return temp

    # Function to stop all body functions, movement and sensing
    def stop(self):
        self.motor_stop()
        sys.exit()

    # TODO: implement the route method
    # def get_pos(self, zone):
    #
    #     if self.gyro_data > 180:
    #         self.gyro_data = 180
    #     if self.gyro_data < -180:
    #         self.gyro_data = -180
    #     print("front: ", self.l1)
    #     print("back: ", self.l2)
    #     print("right: ", self.l3)
    #     print("left: ", self.l4)
    #     print("angle:", self.gyro_data * -1)
    #     print("temp: ", self.temp)
    #
    #     print(Position.find_coordinate(self.gyro_data * -1, self.l1 + 8.0, self.l2 + 8.0, self.l3 + 5.5, self.l4 + 5.5,
    #                                    zone))
    #     pos = Position.find_coordinate(self.gyro_data, self.l1, self.l2, self.l3, self.l4, zone)
    #     self.x = pos[0]
    #     self.y = pos[1]

    def get_pos(self):   ## The one for the 90 degree increment code

        do_function = True

        while do_function:

            angle = self.gyro_data * -1
            l1,l2,l3,l4 = self.get_lidar()

            if angle > 180:     #
                angle = 180     #  Hopefully this shouldn't
            if angle < -180:    #  happen again
                angle = -180    #

            # print("front: ", l1)
            # print("back: ", l2)
            # print("right: ", l3)
            # print("left: ", l4)
            # print("angle:", angle)

            if (angle <= 10 and angle >= -10) or (angle >= 80 and angle <=100) or (angle >=170 or angle<=170) or (angle >=-100 and angle <= -80):

                pos = Position.coordinate_2(angle, l1 + 8.0, l2 + 8.0, l3 + 5.5, l4 + 5.5)

                if pos[0] != 1000:        ## this means no error occured in the coordinate code
                    self.x = pos[0]
                    self.y = pos[1]
                    do_function = False   ## exit function because successful coordinate has been found
                    print("Angle:",angle) ## just for when we want to observe the gyro
                    #temp = self.get_temp()
                    #print("Temperature:",temp)
                    return pos

                if pos[0] == 1000:        ## this means a coordinate could not be found

                    # See which 90-degree increment robot is currently closest to then use PID to rotate to that
                    diffs = [abs(90-angle), abs(-90-angle),abs(180-angle),abs(0-angle)]
                    min_val = min(diffs)

                    if min_val == diffs[0]:
                        closest = 90
                    elif min_val == diffs[1]:
                        closest = -90
                    elif min_val == diffs[2]:
                        closest = 180
                    else:
                        closest = 0

                    self.PID_control_rotate_zero(closest, tol=10)   ## it should do the while loop again after this, attempting coordinate again


    def get_battery_state(self):
        bat = 0.47
        self.battery = bat
        return bat

    def _get_state_info(self):
        # Get information, Dummy Variables for now
        return self.temp, self.x, self.y, self.battery

    def PID_control_rotate_zero(self, closest_angle, error_prior=0, integral=0, error=20, tol=1):

        # result = Position.best_route(desired_coordinate, starting_coordinate, starting_angle)

        ang_desired = closest_angle

        count = 0

        while abs(error) > tol and count < 15:  # error is more accurate than t_rot (as t_rot is based on an estimate)

            error = ang_desired - (-self.gyro_data)
            integral = integral + (error * iteration_time[0])
            derivative = (error - error_prior) / iteration_time[0]

            output = KP[0] * error + KI[0] * integral + KD[0] * derivative + bias[0]  # bias to prevent output being 0
            error_prior = error

            t_rot = abs(output) / W

            if t_rot > 3:
                t_rot=3
            # print(ang_desired)
            # print(error)
            # print(t_rot)

            ## Rotational Movement ##

            if error > 0:
                self.rotate_anti_clockwise()

            else:
                self.rotate_clockwise()

            count += 1

            time.sleep(t_rot)
            self.motor_stop()
            time.sleep(0.1)

        self.motor_stop()

        time.sleep(0.1)  # put in for testing

    ##PID Control function - input the x and y desired coordinate and the starting coordinate (x, y) and starting angle and does rotation and linear movement
    def PID_control_rotate(self, best_route_result, error_prior=0, integral=0, error=20, tol=1):

        # result = Position.best_route(desired_coordinate, starting_coordinate, starting_angle)

        #rot_mov = best_route_result[0]

        # ang_mov = rot_mov[1]

        ang_desired = best_route_result[2]
        print('best_route_result =', best_route_result)
        print('ang_desired main', ang_desired)
        while abs(error) > tol:  # error is more accurate than t_rot (as t_rot is based on an estimate)
            angle = -self.gyro_data
            if angle>=180 or angle<=-180:
                time.sleep(1)
                angle = -self.gyro_data
                print('ANGLE AGAIN =', angle )

            error = (ang_desired - (angle))
            integral = integral + (error * iteration_time[0])
            derivative = (error - error_prior) / iteration_time[0]

            #Should never need to rotate more than 90 , celo
            if abs(error) > 90:
                if error < 0:
                    error = -90
                if error > 0:
                    error = 90  #don't think this is right

            output = KP[0] * error + KI[0] * integral + KD[0] * derivative + bias[0]  # bias to prevent output being 0
            error_prior = error

            t_rot = abs(output) / W
            if t_rot > 3:
                t_rot=3

            #print(ang_desired)
            #print("E:",error," gyro: ",self.gyro_data)
            # print(t_rot)

            ## Rotational Movement ##

            if best_route_result[0][0] == 1:
                if error > 0:
                    self.rotate_anti_clockwise()
                else:
                    self.rotate_clockwise()


            elif best_route_result[0][0] == 0:
                if error > 0:
                    self.rotate_anti_clockwise()
                else:
                    self.rotate_clockwise()
            #print('ang_desired main', ang_desired)
            #print(error)

            time.sleep(t_rot)
            #time.sleep(t_rot)
            self.motor_stop()
            time.sleep(0.1)

        self.motor_stop()

        time.sleep(0.1)  # put in for testing

    def NO_PID_LINEAR(self, best_route_result):
        ##LINEAR MOVEMENT PART##!!!!!!!!!!!!

        lin_mov = best_route_result[1]
        dist = lin_mov[1]

        if abs(dist) > 20:

            if lin_mov[0] == 1:
                self.move_forward()

            elif lin_mov[0] == 0:
                self.move_backward()

            time.sleep(1)  # zone identification will need readings not too dissimilar so that it doesn't reject all zone options
            self.motor_stop()

            time.sleep(0.1)

    def PID_LINEAR(self, best_route_result, error_prior2, integral2=0):

        lin_mov = best_route_result[1]
        dist = lin_mov[1]

        error2 = dist  # or dist-dist_prior
        integral2 = integral2 + (error2 * iteration_time[1])
        derivative2 = (error2 - error_prior2) / iteration_time[1]
        output2 = KP[1] * error2 + KI[1] * integral2 + KD[1] * derivative2 + bias[1]  # bias to prevent output being 0
        self.error_prior2 = error2

        ## Linear Movement ##

        t_lin = output2 / V  # output2 is in cm

        if lin_mov[0] == 1:
            if error2 < 0:
                self.move_backward()
            else:
                self.move_forward()

        elif lin_mov[0] == 0:
            if error2 < 0:
                self.move_forward()
            else:
                self.move_backward()

        # dist_prior=dist
        time.sleep(t_lin)

        self.motor_stop()

        time.sleep(0.1)

        #time.sleep(0.1)

    def PID_COLLISION(self, dir, time2):

        t_lin = time2  # output2 is in cm
        dir = dir;

        if dir == -1:
            self.Current_Dir = -1;
            self.move_backward()
        else:
            self.Current_Dir = 1;
            self.move_forward()

        #Modifying sleep cyclkes to allow interrupt
        #Lesser sleep tp prevent retrggerng /5 not /100
        for i in range(0,5):
            #If LIDAR READING IS TINY THEN START REVERSE BEHAVIOUR
            time.sleep(t_lin/5);
            l1, l2, l3, l4 = self.get_lidar();
            if(l1 < self.l_limit or l2 < self.l_limit or l3 < self.l_limit or l4 < self.l_limit):
                #If LIDAR READING IS TINY THEN START REVERSE BEHAVIOUR
                self.motor_stop()
                #PID_COLLISION((self.Current_Dir*-1),self.Col_Reverse_Time);
                #self.Collision_Chain_Num += 1;
                #could remove ths to on;y allow one collision
                break;


        self.motor_stop()



    def open_loop_control(self, best_route_result):
        lin_mov = best_route_result[1]
        dist = lin_mov[1]
        t_lin = (best_route_result[1][1] / V) - 2

        if lin_mov[0] == 1:
            self.move_forward()

        elif lin_mov[0] == 0:
            self.move_backward()

        time.sleep(t_lin)

        self.motor_stop()
        time.sleep(0.1)

    def PID_movement(self, x_des, y_des,
                    starting_coordinate=(0, 0), starting_angle=0, previous_coordinate=(0,0), count_coordinate = 0):

        best_route_result = Position.best_route((x_des, y_des), starting_coordinate,
                                                starting_angle)  # Decide how to extract variables from this for use below
        print('ang_desired =', best_route_result[2])
        print('Time for the gyro to chill')
        time.sleep(2) #line added to see if this helps

        while best_route_result[1][1] > 20:

            self.PID_control_rotate(best_route_result)

            self.NO_PID_LINEAR(best_route_result)

            starting_coordinate = self.get_pos()# Find position
            #get_temp = self.get_temp()
            #print('Temperature', get_temp)
            #print('Step3')
            print('starting_coordinate =', starting_coordinate)

            ######NEW BIT ADDED IN BELOW


            while ((abs(starting_coordinate[0] - previous_coordinate[0]) > 45) or (abs(starting_coordinate[1] - previous_coordinate[1]) > 45)) and count_coordinate<=10:
                starting_coordinate = self.get_pos()
                #get_temp = self.get_temp()
                #print('Temperature', get_temp)
                print("rotate in ")
                self.PID_control_rotate_zero(0, tol=10)
                time.sleep(0.5)
                print('Checking Coordinate')
                count_coordinate += 1

            if count_coordinate == 10:
                print("count 10")
                starting_coordinate = previous_coordinate #go from last known point
                #t_lin = t_lin-2 #as time moved is 2 seconds. Added in function instead
                self.PID_control_rotate(best_route_result)
                self.open_loop_control(best_route_result)

                starting_coordinate = self.get_pos()

                while starting_coordinate[0]==1000 and starting_coordinate[1]==1000:
                    self.move_forward()
                    print('Checking Coordinate Move Forward')
                    time.sleep(2)
                    starting_coordinate = self.get_pos()
                    #get_temp = self.get_temp()
                    #print('Temperature', get_temp)
                    previous_coordinate = starting_coordinate

            else:
                previous_coordinate = starting_coordinate
            ######NEW BIT ADDED IN ABOVE


            best_route_result = Position.best_route((x_des, y_des), starting_coordinate,
                                                    self.gyro_data)  # Get new best route

            print('ang_desired =', best_route_result[2])
            # Update distance
            #print('Step4')
            time.sleep(1)

        count = 0
        while best_route_result[1][1] > 7:
            #print('Step4.5')
            #print('ang_desired =', best_route_result[2])
            self.PID_control_rotate(best_route_result)
            #print('Step5')
            if count == 0:
                #print('Step5.1')
                self.PID_LINEAR(best_route_result,0)
                count = 1
            else:
                #print('Step5.2')
                self.PID_LINEAR(best_route_result,self.error_prior2)
            #print('Step6')
            #self.PID_control_rotate_zero(closest_angle)
            starting_coordinate = self.get_pos()
            #get_temp = self.get_temp()
            #print('Temperature', get_temp)
            #print('starting_coordinate =', starting_coordinate)


            ######NEW BIT ADDED IN BELOW

            count_coordinate = 0
            while (((abs(starting_coordinate[0] - previous_coordinate[0]) > 40) or (abs(starting_coordinate[1] - previous_coordinate[1]) > 40))) and count_coordinate<=10:
                self.PID_control_rotate_zero(0, tol=10)
                starting_coordinate = self.get_pos()
                #get_temp = self.get_temp()
                #print('Temperature', get_temp)
                time.sleep(0.5)
                if count == 5:
                    print('Checking Coordinate PID')
                count_coordinate += 1

            while count_coordinate == 10 and (starting_coordinate[0]==1000 and starting_coordinate[1]==1000):
                self.move_forward()
                print('Checking Coordinate PID Move Forward')
                time.sleep(2)
                starting_coordinate = self.get_pos()
                #get_temp = self.get_temp()
                #print('Temperature', get_temp)
                previous_coordinate = starting_coordinate

            previous_coordinate = starting_coordinate
            ######NEW BIT ADDED IN ABOVE


            #print('Step7')
            best_route_result = Position.best_route((x_des, y_des), starting_coordinate, self.gyro_data)
            print("linear",best_route_result[1][0])
            #print('Step8')
        self.Arrival_Flag = True
        return True


if __name__ == '__main__':
    # network = Network.SwarmNetwork()
    body = SwarmBody()
    body.duty_cycle = 0.5
    complete = False
    print("[+] Setting Timer")

    while complete == False:
        time.sleep(1)

        if body._get_pos == 1 and body.gyro_data != 0:

            input("Enter character to find coordinate: ")
            position = body.get_pos()
            print(position)
            body.PID_movement(50, 50, starting_coordinate=(position[0],position[1]), starting_angle=position[2])
            position = body.get_pos()
            #break
            print("Coordinate: (",position[0],",",position[1],")")
            #complete = True
            print("REACHED COORDINATE --> (50,50)")
            body.PID_movement(50, 60, starting_coordinate=(position[0],position[1]), starting_angle=position[2])

            position = body.get_pos()
            #break
            print("Coordinate: (",position[0],",",position[1],")")
            #complete = True
            print("REACHED COORDINATE --> (50,70)")
            body.PID_movement(50, 70, starting_coordinate=(position[0],position[1]), starting_angle=position[2])

            position = body.get_pos()
            #break
            print("Coordinate: (",position[0],",",position[1],")")
            #complete = True
            print("REACHED COORDINATE --> (50,80)")
            body.PID_movement(50, 80, starting_coordinate=(position[0],position[1]), starting_angle=position[2])
            position = body.get_pos()


            #best_route_result = Position.best_route((50, 50), (0,0), 0)

            #body.PID_control_rotate(best_route_result)


            position = body.get_pos()
            #break
            print("Coordinate: (",position[0],",",position[1],")")
            #complete = True
            print("REACHED COORDINATE --> (70,70)")
            body.PID_movement(70, 80, starting_coordinate=(position[0],position[1]), starting_angle=position[2])

            position = body.get_pos()
            #break
            print("Coordinate: (",position[0],",",position[1],")")
            complete = True
            print("REACHED COORDINATE --> (70,80)")
            print("Position = ", position)
            body.PID_movement(50, 50, starting_coordinate=(position[0],position[1]), starting_angle=position[2])

        else:
            print("yet again, we are in main")
