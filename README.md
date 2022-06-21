# Catcher server, free productivity tools for cinema exhibitors
![Screen shot of Player-Status screen](images/catcher-screenshot-PlayerStatus.png?raw=true "Screen shot of Player-Status Screen")
## What is a catcher server?
As cinemas transition to an ever more IT centric way of operation, many aspects of running a cinema can be automated.  Catcher is a free to use tool that automates many aspects of running a cinema reducing the running costs.

This tool is focused on smaller cinemas, as some of the features are addressed in larger TMS system bigger operators would already utilise.  However, even larger cinemas may fine the ease of moving content around and a central autonomous LMS and KDM manager desirable.

## Current Status
This tool is still under development and should be considefed Beta Status.  Although some aspects the tools in this are finished, major changes are in the works to implement some of the new advanced features.  Is is expected the major updates should be finished by Feb 2022 and a more production ready version should be available.  However, in the mean time, it would be great if some advanced users could try of the development versiont to contributoe to bugs and potential improvements and suggestions for future developments.

## Feature development status
<pre>
                               Dolby    GDC     Qube    Barco
Player Status Monitor    -     Done    Done     Started Future
Player Status Control    -     Done    Started  Future  Future
--------------------------------------------------------------
Player Status SoundProc  -     Future, JSD100/60
--------------------------------------------------------------
                               Barco   NEC      Christie
Player Status Projector  -     Future  Future   NotPlanned
--------------------------------------------------------------
                               JNOR    RLY8
Player Status IO Box     -     Futrue  Future
--------------------------------------------------------------
                               Dolby    GDC     Qube    Barco
Schedule Status          -     Future   Future  Future  Future
--------------------------------------------------------------
Media Asset solution
Ingest Local Devices                    Done
Ingest from FileSystem                  Done
Ingest from FTP share                   Done
Auto Ingest on discovery                Done
Auto Quality Cheap (Clairmeta)          Done
Auto Delete Older content               Done
Protect from Auto Delete                Done
FTP access to all Ingested              Done
--------------------------------------------------------------
AutoKDM
Creation of Screen data interface       Done
Auto pull Cert from Player              Dolby&Qube Done, GDC&Barco Future
Creation screen to input IMAP sources   Done
Auto download Emails from IMAP source   Done
Auto scan and push found KDMS           Done
Real time email endpoint ingest         Done
Ingest KDM into Players                 Dolby&Qube Done, GDC&Barco Future
--------------------------------------------------------------
Transfers application
This tool is not intended for general use.  It is a DCP distribution system and point implementation
that is part of other solutions such as internal DCP distributrion solutions for cinema chains, advertising
agents or smaller community of DCP content ditribution (i.e. small country adoptions etc.)
Developed to use open standard protocols for security, speed and ease of scaling up as needed.
Contact The develpoper if you are interested in investigating this tool set.
--------------------------------------------------------------
Playout Audit
Finished (Needs testing). Is a tool to monitor and create reports regarding what has been played out 
from specific DCI-Cinema-Players. (Barco, Dolby, GDC, Qube are supported)
This tool allows the user to create complex filters to datamine the logs for numerous reasons. 
It is especially usefull for sending audit of playout for internal or external (Advertising agency) needs.
It can send Emails with attchaed CSV files, or push data directly into JSON endpoints for injecting 
into larger enerprise databases.
</pre>

It is recommended you create an account on GitHub and then monitor this project for updates as so you are informed when new features are made available.  
Plus to report bugs or suggestions, please use your Github account to leave reports on the "Issues" page for this GitHub project.

## Who made the product and why?
The Catcher application was made by a small Australia company (https://www.digitall.net.au) that develops IP for operating autonomous cinema locations.  Due to the COVID crisis and the change in industry norms, such as "Streaming First" initiatives by the major exhibitors and a reduction in windows from 90 to 45 days, the result will be a reduction in attendance for cinemas as consumers change behaviour and take advantage of these offerings.  The objective for making part of the IP available under a free to use model is to ensure the culture of cinemas can metabolize these changes.  For example, if a small cinema loses 10-20% of attendance, but also drops its running costs by 10-20% by becoming more productive in operating the cinema, there is an overall 0 net loss.  Ensuring cinemas are more likely to survive the changes occuring.

digitAll hopes this tool ensures many smaller cinemas can survive and thrive in these difficult times.

## What does Catcher do?
The objective of this application is for do the following:
- Operate as a LMS (Library Management Server), being a central storage of Films/DCPs as they arrive at your cinema.
- Allow ingest from CRU-Disks, USB-Disk, USB-Stick.
- Allow ingest from ftp sources such as is available from delivery devices that are being installed by major DCP-delivery-service providers.  i.e Deluxe, Motion Picture Solutions, etc. (There are numerous.)
- Auto ingest content as it arrives on digital platforms as listed above.
- Move DCPs between cinema locations via FTP.
- QC (Quality Check) all DCPs as they are ingested to ensure they are not corrupted or malformed.
- Automatically manage disk space and age content or delete content when needed. Users can override and protect content from deletion if required.
- Acts as a central location for all incoming content that ensures if a problem exists with content, the cinema operator is informed of this on arrival. This ensures no last minute emergencies occur as problems are only apparent when a user attempts to utilise content.
- Automatically inspects an Email account for any KDM messages, downloads, unzips, and ingests KDM automatically. **Never have to deal with a KDM again.** NOTE: Dolby and Qube IMS are only supported at this time.
- Emails the cinema owners of all activity and specifically if a problem occurs as so the cinema operator can address it before it becomes an emergency.  For example, if a DCP coming into the cinema is corrupted in any way.
- Screen Player monitor overview page (All configured screens), status of current playout, time to credits/finish, time of next event/triggers, time of next scheduled session start.

The catcher application is a set and forget tool.  Typically if everything is going well, you don't even need to log into its interface.

# Supported Cinema Equipment
The following equipment are slated for integration into this toolset.

- Cinema-player: Dolby and Qube is mostly complete.  Barco is coming in 3 months or so, after we can get access to a Barco ICMP to test against (COVID crisis slowing things down a lot). GDC has recently come onboard and will also be supported in coming months.
- Projectors: NEC and Barco are in the works.
- Sound processors: JSD/QSC, Dolby are in the works.
- IO-control: RLY-8 and JNior are in the wortks.

# Reporting bugs and errors
Please utilise the github page and its issue tracker to report issues you may find.

# System Requirements
The recommended hardware and software requirements for Catcher are as follows.
## Hardware
Catcher is a server applications that performs many processes simultaneously and as such needs a modern computer that runs Ubuntu-server (LINUX).  A CPU with 4+ cores with Hyperthreading is recommended.  8Gig of Ram or better.  The computer can have the GUI activated but it is recommended that **no** GUI is used.  A dedicated computer is recommended.  The user accesses the system via a Web browser and so can be used from any computer terminal with a web browser. If GUI is to be used 16 gig ram is recommended.

As this is a LMS and will be storing a large amount of data, the server needs to either have a large amount of disk, or be in a position to mount a large amount of disk from a storage server.  I recommend the following when it comes to disks for the system.
- A 256-500 gig SSD system disk.  This is the target for the operating system.  SSD are very reliable, and having a RAID is not so important these days.  However, over provision the disk ensures it will last a very long time due to how SSDs work and age. (500gig)
- 3 or more storage disks, 4gig or better.  Really depends on how much data you want to store.  3 or more as so they can be raided together using you  prefered RAID solution. (I recommend utilising zfs)

IF you just want to get started, I recommend utilising a single 10gig disk and install the operating system on that disk, and use its extra space for storage.  This avoid the need to implement RAID, however, may be quite slow at some processes due to the lack of IO of a single disk.

## Software
The application is based on **docker** that containerised the application and all the services it needs.  Due to this, you can typically run the application on any **docker** capable server or instance, however, the ability to ingest PHYSICAL disks and USBs is based on ubuntu server.  Ubuntu Server 20.04 LTS is the target operating system to run the catcher application.  However, there is no reason you could not run it virtualized and use a satellite PC that ftp/exports the mounted CRU-Disks/USB-sticks for ingesting.

Typically, when installing a system to run catcher on, you install be base ubuntu-server 20.04 onto a computer.  Install docker-compose, then follow the install procedure below.

## Who is expected to install this for cinema owners?
This is a difficult question.  Cinema owners are businessmen and not IT professionals.  Agents that service cinemas are also more inclined to offer expensive tools that come with 25% yearly maintenance costs.  Many smaller cinemas cannot afford this.

The platform for catcher is based on common open source technologies that cinemas should be able to source reasonable local know how to implement.  The local IT shop, or High-School student level is the target level of expertise.  I know many cinema owners that would be able to figure this out themselves and enjoy the challenge of doing so.

The install path is:  Get suitable hardware, install Ubuntu Server, follow these install instructions below.

# How to install Catcher
## Ready your server
Before you continue, the server needs a number of items.
- Make the storage directory andmount your storage disk onto that directory.
- Network and IP address configuration.

### Mounting storage disk
You must make the following directories and mount your storage disk onto the directory.
```
$ sudo mkdir /opt/catcher
$ sudo mkdir /opt/catcher/storage
```
This is where some LINUX knowhow comes in handy as the storage disk, be it a Hardware RAID, software RAID under linux, other mounted from a storage server, must be mounted on the `/opt/catcher/storage` directory.  I recomend you google how this is done based on your requirements.

If you are just taking the simple path and installed the Ubuntu-server onto a large disk, you only need to make the directories.  If nothing is mounted on the `storage` directory, the files will be stored on the '/' or root filesystem same as the opertating system in installed upon.

### Setup your network interfaces
It is recommended that the server has two physical Network interfaces.  One on the typical Internet connected network, and the second on the Projection network.  Many cinemas keep the Projection network on a physically isiloted network so it cannot reach into the internet.  As the catcher needs to talk to the projection network devices and is also likely to pull content from the internet, it will need two seperate interfaces connections, one for each. NOTE: some smaller cinemas, keep this all on the same physical network.  This is simpler for them, and if it works. It works, and is easier to manage.  But in general, seperate physical networks are recommended.

The projection network requires a STATIC IP address as it needs to be refered to in the `docker-compose.yml` file.

## Installing the software
Enter the folowing commands at the command prompt after you login.
```
$ sudo apt install git docker-compose
```
NOTE: You will be asked for your password whenever you use `sudo`, or **SuperUser DO** which runs the command as the root/super user.

This will install the docker subsystem that Catcher will run upon and git, so you can download the example `docker-compose.yml` file.
```
$ cd /opt
$ sudo git clone https://github.com/jamiegau/cinema-catcher-app.git
```
This will download the example yml config file and other files into a direcory called cinema-catcher-app.  In this directory you control the docker containers and bring up the applicatin and all its services.

## Create the configuration file.
Create a file called `local.env.sh` file is in the directory `/opt/cinema-catcher-app`.
```
$ cd /opt/cinema-catcher-app
$ sudo nano local.env.sh
```
`nano` is a basic text editor, but `vi` or whatever text editor you are confitable with can be used.

Copy the following into the file:
```
LOCAL_TIMEZONE_NAME=Australia/Brisbane
CATCHER_HOSTNAME=catcher-location-name
EXPOSED_IP_PROJECTION_NETWORK=x.x.x.x
export LOCAL_TIMEZONE_NAME CATCHER_HOSTNAME EXPOSED_IP_PROJECTION_NETWORK
```
Update these three variables as described by their names.
`EXPOSED_IP_PROJECTION_NETWORK` is the static IP address you assigned to the network interface on the projection network.

Set the TIMEZONE_NAME environement variable.  This should be set to, for example
`Melbourne/Australia` or the suitable name for your location. (see https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for a list of names.)

Make sure the following files are executable with this command
```
$ chmod 755 local.env.sh TAIL.sh update.sh start.sh
```
Source the local.env.sh file to make sure your local config is set in your shell.
```
$ ./local.env.sh
```

### Download the software
Once you have created the local config file.  Its time to pull down all the software from the docker-hub.  To do this type:
```
$ sudo docker-compose pull
```
This will take some as neat 2GB of applications will be downloeded.  Get a coffie..

Once this has completed, type the next command to initialise the install (ie, the database etc.)
```
sudo docker-compose run backend python3 ./manage.py migrate
sudo docker-compose run backend python3 ./manage.py catcher_setup
```
And finally, start the server.
```
sudo docker-compose up -d
```
You can now type the IP address of the Catcher Server into a browser and continue with the setup of the software.
If you reboot the server, the docker service should shutdown and restart the catcher docker containers automatically.

### Other usefull commands
```
sudo docker-compose ps
```
To get the status of the containers.

In the same folder at the config file you will find the command `TAIL.sh` (make sure you `chmod 755 TAIL.sh`, so you can execute it as a command first), use this command to monitor the debug output of all (done supply any docker container name) of a specific container by giving it the container name.  i.e.
```
sudo TAIL.sh backend
```
Shutdown the catcher server.
```
sudo docker-compose down
```
Update the server to latest version of the containers by using the `update.sh` script (make sure you `chmod 755 update.sh`, so you can execute it as a command first).  It will shutdown, pull latest containers, update the database if required,  bring the catcher containers back up and delete any older container file left behind.  All in one command.
```
sudo update.sh
```

# Setting up the Software

In the near future a Video tutorial will be created.
For not, please refer to these other Manuals

General Catcher Manual [Click to Read](Manual.md)

AutoKDM Manual [Click to Read](Manual_AutoKDM.md), Note, only Dolby and Qube DCI-players are currently supported.  GDC and Barco will be aded in time.
