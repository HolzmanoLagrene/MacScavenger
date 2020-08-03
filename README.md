# MacScavenger

The MacScavenger is a system built to  circumvent such 
MAC address randomization by applying signal 
strength-based localization to distinguish different 
devices otherwise non-distinguishable by looking at 
the information they contain.

It consists of four main components:
- The Shell: Responsible for user interaction
- The Monitors: Responsible for data collection
- The Sync: Responsible for interacting and synchronizing the monitor nodes and store the data.
- The Analyzer: Responsible for interpreting the collected data

The user interacts with the system by starting the Shell via
`python  MacScavengerShell.py`. From there the different possible commands
 are listed typing `help`.
 
 The two main uses of the MacScavenger are Data Collection and Data Analysis:
 ### Data Gathering
 To gather data, the code for the monitor nodes must be started via `python MacScavengerMonitor.py PORT_NUMBER` on the devices responsible for data collection.
 After successfully deploying the monitor nodes, the Shell is used to start and stop the data collection process by tying
 `setup`, `start` or `stop`.
 
 To configure a valid database source for storing the monitored data. A folder must be placed
  in the folder `SyncDataBaseInterfaces`, implementing the interface `SyncDataBaseBaseClass`.
  This class can then be loaded in the `MacScavengerSync` class and assigned as database with the following code:\
  `self.database = CustomDataBase()`.
 
 ### Data Analysis
The data anlysis process is started via the shell by typing
`analyze` into the shell.


### Demo
The analysis process can be tested by using the `total_data.json` file in the folder `json_data`:
```
Welcome! Type ? to list commands
MacScavenger> analyze

Please enter Access Point Positons in the following form {"ap1":(0,0), "ap2":(5,0),"ap3":(5,5),"ap4":(0,5)}
{"tinkerboard1":(0,0),"tinkerboard2":(2,1),"tinkerboard3":(2,5),"tinkerboard4":(0,0)}

Analyzer has the following Configuration:
- Interval Size in seconds: 10
- Assumed Walking Speed in km/h: 2
- In Burst Time Threshold in seconds: 1
- Min. AP detection Rate: 3
- Verbosity: 0
Do you agree with this configuration? Type y/n!
y

Please enter a valid data path
json_data/total_data.json

The specified data source is a valid file
Starting Analysis ...

Summary:                                                                             
Approximately 425 different recognizable devices on site that were detected by at minimum 3 APs
Thereof, 425 devices were seen just once, while 370 were seen multiple times
301 devices were using MAC Randomization, 69 were not applying Randomization techniques
```