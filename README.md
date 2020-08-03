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