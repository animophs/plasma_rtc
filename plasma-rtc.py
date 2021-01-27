#!/usr/bin/python

import os
import sys
import time
import datetime
import RPi.GPIO
import RPiI2C
import socket
import struct

# DS1307 Constants.
DS1307_CTRL_OUT = 0x80
DS1307_CTRL_SQWE = 0x10
DS1307_CTRL_RATE_0 = 0x00
DS1307_CTRL_RATE_1 = 0x01
DS1307_CTRL_RATE_1HZ = 0x00
DS1307_CTRL_RATE_4KHZ = 0x01
DS1307_CTRL_RATE_8KHZ = 0x02
DS1307_CTRL_RATE_32KHZ = 0x03

DS1307_CTRL_BYTE = (DS1307_CTRL_OUT | DS1307_CTRL_SQWE | DS1307_CTRL_RATE_1HZ)

DOW = [ "",          "Sunday",   "Monday", "Tuesday", \
        "Wednesday", "Thursday", "Friday", "Saturday" ]

# I2C Command Data. To read specific register, write addres, then read data.
# WRITE: [READ_COUNT, [DS1307_ADDRESS + 0], REG_ADDRESS, DATA, DATA, ...]
# READ:  [READ_COUNT, [DS1307_ADDRESS + 1]]
DS1307_WRITE_ALL  = [0,  [0xD0, 0x00]]
DS1307_READ_ALL   = [64, [0xD1]]
DS1307_WRITE_TIME = [0,  [0xD0, 0x00]]
DS1307_READ_TIME  = [3,  [0xD1]]
DS1307_WRITE_DATE = [0,  [0xD0, 0x03]]
DS1307_READ_DATE  = [4,  [0xD1]]
DS1307_WRITE_CTRL = [0,  [0xD0, 0x07]]
DS1307_READ_CTRL  = [1,  [0xD1]]
DS1307_WRITE_MSG  = [0,  [0xD0, 0x08]]
DS1307_READ_MSG   = [56, [0xD1]]

print("Python version")
print (sys.version)
print("Version info.")
print (sys.version_info)

# Initialise GPIO.
RPi.GPIO.setwarnings(False)
RPi.GPIO.setmode(RPi.GPIO.BCM)
RPiI2C.I2C_Init()

def get_ntp_time(host = "pool.ntp.org"):
        port = 123
        buf = 1024
        address = (host,port)
        msg = '\x1b' + 47 * '\0'

        # reference time (in seconds since 1900-01-01 00:00:00)
        TIME1970 = 2208988800 # 1970-01-01 00:00:00

        try:
            # connect to server
            client = socket.socket( socket.AF_INET, socket.SOCK_DGRAM)
            client.settimeout(3)
            client.sendto(msg.encode('utf-8'), address)
            msg, address = client.recvfrom( buf )

            t = struct.unpack( "!12I", msg )[10]
            t -= TIME1970

            # return time.ctime(t).replace("  "," ")
            return t
        except Exception as e:
            return None

def update_system_time_from_rtc():
    SetText = ""

    RPiI2C.I2C_SendReceiveData(DS1307_WRITE_DATE[1])
    Result = RPiI2C.I2C_SendReceiveData(DS1307_READ_DATE[1], DS1307_READ_DATE[0])
    SetText += "sudo date -s '20{:02X}-{:02X}-{:02X} ".format(Result[3], Result[2], Result[1])

    RPiI2C.I2C_SendReceiveData(DS1307_WRITE_TIME[1])
    Result = RPiI2C.I2C_SendReceiveData(DS1307_READ_TIME[1], DS1307_READ_TIME[0])
    SetText += "{:02X}:{:02X}:{:02X}'".format(Result[2], Result[1], Result[0])

    os.system(SetText)

    # Change timezone
    TimeZone = "sudo timedatectl set-timezone Asia/Ho_Chi_Minh"
    os.system(TimeZone)

def update_time_to_rtc(current_time):
    # Set the DS1307 with the current system date.
    SetData = list(DS1307_WRITE_DATE[1])
    Day = current_time.tm_wday + 2
    if Day > 7:
     Day = 1
    SetData.append(Day)
    SetData.append((current_time.tm_mday % 10) + (int(current_time.tm_mday / 10) << 4))
    SetData.append((current_time.tm_mon % 10) + (int(current_time.tm_mon / 10) << 4))
    SetData.append(((current_time.tm_year - 2000) % 10) + (int((current_time.tm_year - 2000) / 10) << 4))
    RPiI2C.I2C_SendReceiveData(SetData)

    # Set the DS1307 with the current system time.
    SetData = list(DS1307_WRITE_TIME[1])
    SetData.append((current_time.tm_sec % 10) + (int(current_time.tm_sec / 10) << 4))
    SetData.append((current_time.tm_min % 10) + (int(current_time.tm_min / 10) << 4))
    SetData.append((current_time.tm_hour % 10) + (int(current_time.tm_hour / 10) << 4))
    RPiI2C.I2C_SendReceiveData(SetData)

def main():
    update_system_time_from_rtc_flag =  False
    update_system_time_from_rtc_tick_sec = 0
    update_system_time_from_rtc_period = 5

    update_internet_time_to_rtc_tick_sec = 0
    update_internet_time_to_rtc_period = 10
    rtc_detect_flag = False

    while True:
        # RTC detection
        if RPiI2C.I2C_Check(0xD0) == 0:
            rtc_detect_flag = True
        else:
            rtc_detect_flag = False

        if update_system_time_from_rtc_tick_sec >= update_system_time_from_rtc_period:
            update_system_time_from_rtc_tick_sec = 0
            if update_system_time_from_rtc_flag == False :
                try:
                    if rtc_detect_flag is True:
                        update_system_time_from_rtc()
                        update_system_time_from_rtc_flag = True
                        print("Get time from RTC")
                    else:
                        print("RTC not detected")
                except Exception as e:
                    update_system_time_from_rtc_flag = False
                    print(str(e))

        if update_internet_time_to_rtc_tick_sec >= update_internet_time_to_rtc_period:
            update_internet_time_to_rtc_tick_sec = 0
            tm = get_ntp_time()
            if tm is not None:
                try:
                    if rtc_detect_flag is True:
                        update_time_to_rtc(time.gmtime(tm))
                        update_internet_time_to_rtc_period = 15#300
                        print("RTC time updated")
                    else:
                        print("RTC not detected")
                except Exception as e:
                    update_internet_time_to_rtc_period = 10
                    print(str(e))
            else:
                print("No internet connection")

        update_internet_time_to_rtc_tick_sec += 1
        update_system_time_from_rtc_tick_sec += 1
        time.sleep(1)


if __name__ == '__main__':
    main()
