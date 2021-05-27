# Catcher server for cinema exhibitors
## What is a catcher server?
As cinemas transition to an ever more IT centric way of operation, many aspects of running a cinema can be automated.  Catcher is a free to use tool that automates many aspects of running a cinema reducing the running costs.

This tool is focused on smaller cinemas, as some of the features are addressed in larger TMS system bigger operators would already utilise.  However, even larger cinemas may fine the ease of moving content around and a central autonomous LMS and KDM manager desirable.

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

The catcher application is a set and forget tool.  Typically if everything is going well, you don't even need to log into its interface.

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

## Editing the configuration file.
The yml config file is in the directory `/opt/cinema-catcher-app`.
```
$ cd /opt/cinema-catcher-app
$ sudo nano docker-compose.yml
```
`nano` is a basic text editor, but `vi` or whatever text editor you are confitable with can be used.

In the configuration file, you will file some aread with `#` comments.
There are 3 areas to edit before we start the catcher server processes.

Firstly, set the hostname of the catcher-server
```
backend:
    image: jamiegau/catcher_backend:3.0
    restart: always
    # Set the HOSTNAME the catcher instance will be know as in the conteiner.
    # for example, catcher-CINEMA-LOCATION such as catcher-chain-state or catcher-clubmovie-forbes
    hostname: catcher-example
```

Second, set the static IP address you assigned to the network interface on the projection network.  This appear twice in the yml file.
```
extra_hosts:
      - "host.docker.internal:10.30.1.3"
```
In this case, set `10.30.1.3` to the projection netwrok interface static IP.

Once you have edited the ml file.  Its time to pull down all the software from the docker-hub.  To do this type:
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

# Setting up the Software

