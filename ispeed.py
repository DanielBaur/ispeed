

#####################################################
### Imports
#####################################################


import speedtest
import subprocess
import time
import getpass
import argparse
import numpy as np
import os
import sqlite3
import datetime
import matplotlib.dates as mpldt
from matplotlib.dates import  DateFormatter





#####################################################
### Initial Definitions
#####################################################


# determining the current user
username = getpass.getuser()
if username == "daniel":
    machine = "x380"
elif username == "pi":
    machine = "raspi"
    import RPi.GPIO as GPIO
else:
    raise Exception(f"The user could not be determined: {username}")


# grabbing the relevant IP addresses
data_dict = {
    "x380" : {
        "WLAN" : "192.168.0.128",
        "Ethernet" : "169.254.212.79", # 127.0.0.1
        "path_project" : "/home/daniel/Desktop/projects/ispeed/",
        "path_data" : "/home/daniel/Desktop/projects/ispeed/data/",
        "username" : "daniel"
    },
    "raspi" : {
        "WLAN" : "192.168.0.210",
        "Ethernet" : "192.168.0.209",
        "path_project" : "/home/pi/Desktop/ispeed/",
        "path_data" : "/home/pi/Desktop/ispeed/data/",
        "username" : "pi"
    }
}


# stuff
filename_database = "ispeed.db"
filename_thisfile = "ispeed.py"
database_tablename = "ispeed_data"
sqlite_db_format = "(datetimestamp, interface, download_mbitps, upload_mbitps, ping_ms)" # this is the format (i.e. the names of the columns) of the database table
sleeptime = 5 # in seconds





#####################################################
### Helper Functions
#####################################################


# This function is used to generate a datestring (e.g. datetimestring() ---> "20190714_1740" for 14th of July 2019, 17:40h)
def datetimestring(flag_separatedateandtimewithunderscore=False):
    datestring = str(datetime.datetime.today().year) +str(datetime.datetime.today().month).zfill(2) +str(datetime.datetime.today().day).zfill(2)
    timestring = str(datetime.datetime.today().hour).zfill(2) +str(datetime.datetime.today().minute).zfill(2) +str(datetime.datetime.today().second).zfill(2)
    if flag_separatedateandtimewithunderscore == False:
        return datestring +timestring
    else:
        return datestring +"_" +timestring


# This function is used to measure the current upload and download speeds.
def measure_ispeed(ipstring):
    try:
        a = subprocess.run(["speedtest-cli", "--source", ipstring], stdout=subprocess.PIPE)
        b = str(a.stdout.decode('utf-8')).split("\n")
        download_mbitps = float(b[6][10:-7])
        upload_mbitps = float(b[8][8:-7])
        ping_ms = float(b[4][b[4].index("]:")+3:-3])
        #print(f"Download: {download_mbitps}")
        #print(f"Upload: {upload_mbitps}")
        #print(f"Ping: {ping_ms}")
    except:
        print("exception occurred")
        download_mbitps = -1
        upload_mbitps = -1
        ping_ms = -1
    return download_mbitps, upload_mbitps, ping_ms


# This function is used to add an entry to a SQLite database file.
def add_entry_to_sqlite_database(
        dbconn,
        values, # tuple: (datetimestamp, interface, download, upload, ping)
        tablename = database_tablename,
        databaseformat = sqlite_db_format
    ):
    # writing the command to add data to the database into a multiple line string
    qmstring = str(("?",)*len(values))
    #print(qmstring)
    sqlstring = "INSERT INTO {}{} VALUES(?, ?, ?, ?, ?)".format(tablename, databaseformat)
    #print(sqlstring)
    cur = dbconn.cursor()
    cur.execute(sqlstring, values)
    return


# This function is used to
def set_raspi_led(led_val):

    # setup
    led_pin = 21
    if led_val in ["high", 1, "on"]:
        led_voltage = GPIO.HIGH
    elif led_val in ["low", 0, "off"]:
        led_voltage = GPIO.LOW
    else:
        raise Exception("No valid input for 'led_val': {}".format(led_val))
        
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(led_pin,GPIO.OUT)

    # setting the LED voltage
    GPIO.output(led_pin,led_voltage)
    GPIO.output(led_pin,led_voltage)

    return 
    

# This function is used to search for the latest database file.
def get_latest_filename():
    timestamp_list = [int(filename.split("__")[0].split("_")[0] +filename.split("__")[0].split("_")[1]) for filename in os.listdir(data_dict["x380"]["path_data"])]
    m = str(max(timestamp_list))
    m1 = m[:8]
    m2 = m[-6:]
    return m1+"_"+m2


# This function is used to convert the datetimestamps of the db_ndarray ('yyyymmddhhmmss') into datetimes and then into the plt.-interpretable date format
def plt_dates(input_ndarray):
    
    # converting the datetimestamps into a plt.-interpretable date format
    datetimestamps = input_ndarray["datetimestamp"]
    datetimes = [datetime.datetime.strptime(str(i), '%Y%m%d%H%M%S') for i in datetimestamps]
    plt_dates = mpldt.date2num(datetimes)
    
    # extracting the midnight timestamps
    minmax = [min(input_ndarray["datetimestamp"]),max(input_ndarray["datetimestamp"])]
    midnight_ts_i = int(str(minmax[0])[:8] +"000000")
    plt_midnight_dates = [str(midnight_ts_i)]
    while midnight_ts_i <= minmax[1]:
        midnight_ts_i = midnight_ts_i+1000000
        plt_midnight_dates.append(str(midnight_ts_i))
    midnight_datetimes = [datetime.datetime.strptime(str(i), '%Y%m%d%H%M%S') for i in plt_midnight_dates]
    plt_midnight_dates = mpldt.date2num(midnight_datetimes)
    return [plt_dates, plt_midnight_dates]





#####################################################
### Main: init, display, finish, update
#####################################################







#####################################################
### Main
#####################################################


# This is the main function used to retrieve the readings from the 'Prozessabbild' of the RevPi.
def ispeed_main():

    # deleting old database file
    #subprocess.call("rm "+data_dict[machine]["path_project"] +filename_database, shell=True)

    # generating new database file
    new_dbname = datetimestring(flag_separatedateandtimewithunderscore=True) +"__" +filename_database
    conn = sqlite3.connect(data_dict[machine]["path_data"] +new_dbname)
    sql_ispeed_table_string = """ CREATE TABLE IF NOT EXISTS {} (
                                datetimestamp integer NOT NULL,
                                interface text NOT NULL,
                                download_mbitps real NOT NULL,
                                upload_mbitps real NOT NULL,
                                ping_ms real NOT NULL
                             ); """.format(database_tablename)
    conn.execute(sql_ispeed_table_string)
    conn.commit()
    conn.close()
    
    # constantly testing the upload and download speed and writint it into a database
    ctr = 0
    #while ctr <= 1:
    while True:
        for interface in ["WLAN", "Ethernet"]:

            set_raspi_led(led_val="on")

            # measuring the current upload and download speed
            download_mbitps, upload_mbitps, ping_ms = measure_ispeed(ipstring=data_dict[machine][interface])

            # writing the files into the database
            datetimestamp = int(datetimestring())
            values = (datetimestamp, interface, download_mbitps, upload_mbitps, ping_ms)
            conn = sqlite3.connect(data_dict[machine]["path_data"] +new_dbname)
            add_entry_to_sqlite_database(dbconn=conn, values=values, tablename=database_tablename, databaseformat=sqlite_db_format)
            conn.commit()
            conn.close()

            # printing the current readings to the screen
            print(f"{interface}")
            print(f"datetime: {str(datetimestamp)[:8] +'_' +str(datetimestamp)[-6:]}")
            print(f"download: {download_mbitps} Mbit/s")
            print(f"uplaod: {upload_mbitps} Mbit/s")
            print(f"ping: {ping_ms} ms\n")

            set_raspi_led(led_val="off")

        ctr += 1
        blinkinterval_per_sleeptime = 4
        for i in range(blinkinterval_per_sleeptime):
            set_raspi_led(led_val="on")
            time.sleep((1/blinkinterval_per_sleeptime*2)*sleeptime)
            set_raspi_led(led_val="off")
            time.sleep((1/blinkinterval_per_sleeptime*2)*sleeptime)

    return


# This function is used from the x380 to copy the current version of ispeed.py onto the raspi.
def ispeed_update():

    # copying the current version of this file onto the raspi machine
    execstring = "scp " +data_dict["x380"]["path_project"] +filename_thisfile +" " +data_dict["raspi"]["username"] +"@" +data_dict["raspi"]["WLAN"] +":" +data_dict["raspi"]["path_project"] +filename_thisfile
    print(execstring)
    subprocess.call(execstring, shell=True)

    return


# This function is used from the x380 to just copy the acquired data via WiFi over onto the x380 machine (without interrupting the current data taking).
def ispeed_copy():

    # retrieving the slow control data .db file
    execstring = "scp -r {}:{} {}".format(data_dict["raspi"]["username"] +"@" +data_dict["raspi"]["WLAN"], data_dict["raspi"]["path_data"] +"*", data_dict["x380"]["path_data"])
    print(execstring)
    subprocess.call(execstring, shell=True)

    return


# This function is used from the x380 to initiate the data acquisition at the raspi.
def ispeed_init():

    # initializing the DAQ on the raspi machine and detaching it to a separate screen
    initstring = "ssh {} screen -Sdm ispeed python3 {} --runmode main".format(data_dict["raspi"]["username"] +"@" +data_dict["raspi"]["WLAN"], data_dict["raspi"]["path_project"] +filename_thisfile)
    print(initstring)
    subprocess.call(initstring, shell=True)

    return


# This function is used from the x380 to stop the data acquisition at the raspi, copy the acquired data via WiFi over onto the x380 machine and delete it on the raspi afterwards.
def ispeed_finish():

    # killing the slow control process on the raspi
    subprocess.call("ssh -t {} screen -XS ispeed quit".format(data_dict["raspi"]["username"] +"@" +data_dict["raspi"]["WLAN"]), shell=True)

    # retrieving the slow control data .db file
    subprocess.call("scp -r {}:{} {}".format(data_dict["raspi"]["username"] +"@" +data_dict["raspi"]["WLAN"], data_dict["raspi"]["path_data"] +"*", data_dict["x380"]["path_data"]), shell=True)

    return





#####################################################
### Executing Main
#####################################################


# loading a list containing 
if __name__=="__main__":

    # processing the input given when this file is executed
    parser = argparse.ArgumentParser(description='Initialize ispeed.py .')
    parser.add_argument('-r', '--runmode', dest='runmode', type=str, required=False, default="slow_control")
    runmode = parser.parse_args().runmode


    # case 1: running the slow control (default)
    if runmode in ["main"]:
        ispeed_main()


    # case 2: finishing the current run
    elif runmode in ["f", "finish", "finished", "final", "fin", "stop", "interrupt"]:
        ispeed_finish()


    # case 3: update the 
    elif runmode in ["u", "update"]:
        ispeed_update()


    # case 4: update the 
    elif runmode in ["c", "copy"]:
        ispeed_copy()


    # case 5: invalid input
    else:
        print("That's falsch!")
        print("It's not working.")
        print("But it should.")
        print("It isn't.")
        print("But it should...")
