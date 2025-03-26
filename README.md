# Catcher server, free productivity tools for cinema exhibitors

![Screen shot of Player-Status screen](images/catcher-screenshot-PlayerStatus.png?raw=true "Screen shot of Player-Status Screen")

## What is a catcher server?

As cinemas transition to an ever more IT-centric way of operation, many aspects of running a cinema can be automated.
Catcher is a free-to-use tool that automates many aspects of running a cinema reducing running costs.

This tool is focused on smaller cinema exhibitors that may not be using a TMS due to costs. For larger Exhibitors or
chains who want a free backup solution, independent of the TMS. There are many features in the software that do not
exist in TMS vendor software. This is software written by a cinema owner and the problems they have, and not
vendor-driven software with a set agenda.

**Documentation on suitable equipment and the installation process is below.**

## Current Status

This tool is still under development and should be considered Beta Status. Although some aspects of the tools are
finished, major changes are in the works to implement some of the new advanced features. Many tools in this software
should be considered projection ready. However, with the numerous combinations of software possible, it would be great
if some advanced users could try out the development versions and contribute to bugs and potential improvements and
suggestions for future developments.

## Ready for Production

The following features are ready for production. The goal of the system is a set-and-forget solution that should only
need updating if a problem or change in equipment occurs. Its focus is to reduce labor in dealing with technical aspects
of running a cinema as much as possible. The system operates completely independently of any TMS, and as such can be
used to back up any TMS functions or operate to address the specific operation functions it automates. It is designed to
be used on a site-by-site basis, or as a global tool looking after numerous sites and hundreds of screens.

The features of the catcher application are also independent and the user can use one or more of the tools it comes with
depending on their needs. It is not all or none. Its ala carte. Only utilise the tools that best suit you.

| Feature                         | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Status                                                                          |
|---------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| LMS (Library Management System) | This feature includes the ability to ingest content from  physical disks and USBs or from FTP servers, local or remote.  Devices can be set to periodically scan and ingest any DCP found.  ClairMeta is then used to Quality-Check the DCP.  Finally, Email reports can be generated automatically. Oldest Assets are automatically deleted as needed. Assets can be marked to never delete. As a LMS, all content is then made available via FTP server, for Screen-DCI-Player to ingest any content in the Library. <br/><br/>New Feture, FTP upload DCP into LMS capability<br/><br/>Online Video Overview: https://youtu.be/G0GvkAnYvt0                                                                                                                                                                                                                                           | Production                                                                      |
| Status Monitor                  | This tool allows you to monitor all screen configured into the system.  Ths can be used to monitor local or numerous remote screens                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Production limited functionality                                                | 
| Status Monitor device Control   | Under development and extending the status Monitor, you can take control of any DCI-Player, Sound-processor, Projector, IO-Device directly to override or manually control a screen if required                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Development                                                                     |
| Schedule Monitor                | This screen monitors screens on a Schedule level showing a timeline for each screen and what sessions are playing at what time and when they finish/start                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Not Started                                                                     |
| AutoKDM                         | Is a tool that can monitor an IMAP access to an Email account.  It will transparently read your Email, and only download Emails that contain KDMs, mark them as read, or even move them into another folder (Only if a KDM is discovered).  It is best to have a dedicated Email for KDMs however, the tool can deal with utilising an Email that is also used by humans for general Email activity.  The tool will download all KDMs into a data base for checking, tracking and finally ingesting into the target player.  Based on configured target players, AutoKDM will ingest KDMs automatically to all target screens automatically.  Reports on activity can be emailed to the Admin if required. The system incorporates KDM INFO Emails for users can easily track back to the KDM creator if problems occur. <br/><br/>Online Video Overview: https://youtu.be/zjN9h2T82js | Production                                                                      |
| KDM Alert                       | This tool generates daily reports sent to the Staff that inform of any scheduled session that do not yet have a KDM to allow them to play.  This tool ensures a cinema knowns days in advance if a KDM has failed to arrive, giving them time to react to the error. <br/><br/>Online Video Overview: https://youtu.be/1WV9WR4vVxM                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Production                                                                      |
| Auto Discovery                  | Based on the open source tool cinema-nmap-scripts (https://github.com/jamiegau/cinema-nmap-scripts).  It will automatically detect well known devices on the Projection network, pulling Version numbers when possible.  The tool can then be used to audit your projection equipment and can automatically detect the change in any version of DCI-equipment sending/Emailing a Report when changes occur.  Plans to incorporate this with an FLM tool has been discussed.) <br/><br/>Tool Overview: https://youtu.be/7JnhEDdOobo <br/>NMAP tool: https://youtu.be/1ZUCCIH4OYA                                                                                                                                                                                                                                                                                                        | Production, but limited by devices supported in the cinema-nmap-scripts project |
| Player Audit                    | This tool periodically downloads playout logs from the DCI-Players.  This allows the creation of reports to analyise the activity on a player.  This can be used to send playout reports for Advertisers or for engineers to get a detailed indication of the activity on a player. For example, you can detect if shows are playing outside of open hours, or if manual control is occurring and how often. This can be done by either an Email report containing a CSV-file, or automatically sending playout reports to a specified WEB End-point (Internet Web Address) that the data is pushed to periodically. <br/><br/> Tool Overview: https://youtu.be/7ZEj2FhvOis                                                                                                                                                                                                            | Production                                                                      |

## Feature development status

|                       | Dolby   | GDC     | Qube    | Barco   |
|-----------------------|---------|---------|---------|---------|
| Player Status Monitor | Done    | Done    | Started | Started |
| Player Status Control | Partial | Started | Partial | Future  |

|                                | Status | Vendors   |
|--------------------------------|--------|-----------|
| Player Status Sound-Processors | Future | JSD100/60 |

|                         | Barco  | NEC    | Christie         |
|-------------------------|--------|--------|------------------|
| Player Status Projector | Future | Future | long term Future |

|                      | JNIOR  | RLY8   | KMTronic |
|----------------------|--------|--------|----------|
| Player Status IO Box | Futrue | Future | Future   |

|                         | Dolby  | GDC    | Qube   | Barco  |
|-------------------------|--------|--------|--------|--------|
| Schedule Status Monitor | Future | Future | Future | Future |

| Media Asset Solution Features  | Progress |
|--------------------------------|----------|
| Ingest Local Devices           | Done     |
| Ingest from FileSystem         | Done     |
| Ingest from FTP share          | Done     |
| Auto Ingest on discovery       | Done     |
| Auto Quality Cheap (Clairmeta) | Done     |
| Auto Delete Older content      | Done     |
| Protect from Auto Delete       | Done     |
| FTP access to all Ingested     | Done     |

| AutoKDM and Alert-KDM Features           | Progress (Dolby, GDC, Qube, Barco)      |
|------------------------------------------|-----------------------------------------|
| Creation of Screen data interface        | Done                                    |
| Auto pull Cert from Player               | Done                                    |
| Creation screen to input IMAP sources    | Done                                    |
| Auto download Emails from IMAP source    | Done                                    |
| Auto scan and push found KDMS            | Done                                    |
| Real time email endpoint ingest          | Done                                    |
| Ingest KDM into Players                  | Done                                    |
| Real time Email to KDM ingest            | Possible but needs extra infrastructure |
| Schedule inspect                         | Done                                    |
| Schedule to Session/CPL matching         | Done                                    |
| Schedule/Session/CPL to KDM matching     | Done                                    |
| Report generation and Email              | Done                                    |
| Report setup, history and manual control | Done                                    |

# Documentation

Detailed documentation is built into the tool and typically can be found in the menus section of the toolset your are
using.

It is recommended you create an account on GitHub and then monitor this project for updates as so you are informed when
new features are made available.  
Plus to report bugs or suggestions, please use your Github account to leave reports on the "Issues" page for this GitHub
project.

# "Transfer" application

This tool is a part of a content distribution solutions that was prototyped into the catcher applications. It is part of
the https://admin.d-cine.net online toolset targeting exhibitors and distributors. Based on automated booking system (
see overview: https://youtu.be/a8fPI5D-gbU), the solution will route content automatically to exhibition locations.

It also performs detailed online QC of DCPs. (Biterate, AutoLevels, Clairmeta certification, online preview.)

This is a proof of concept toolset and has been mostly completed and in production for a small cinema chain. However, it
can be expanded to small regions. Contact the developer if interested in leveraging this implementation for DCP
distribution solutions for cinema chains, advertising agents or a smaller community of DCP content distribution (i.e.
small country adoptions etc.) Developed to use open standard protocols for security, speed and ease of scaling up as
needed. Contact The developer if you are interested in investigating this tool set.

# Who made the product and why?

The Catcher application was made by a small Australia company (https://www.digitall.net.au) that develops IP for
operating autonomous cinema locations. Due to the COVID crisis and the change in industry norms, such as "Streaming
First" initiatives by the major exhibitors and a reduction in windows from 90 to 45 days, the result will be a reduction
in attendance for cinemas as consumers change behaviour and take advantage of these offerings. The objective for making
part of the IP available under a free to use model is to ensure the culture of cinemas can metabolize these changes. For
example, if a small cinema loses 10-20% of attendance, but also drops its running costs by 10-20% by becoming more
productive in operating the cinema, there is an overall 0 net loss. Ensuring cinemas are more likely to survive the
changes occuring.

digitAll hopes this tool ensures many smaller cinemas can survive and thrive in these difficult times.

# Supported Cinema Equipment

The following equipment are slated for integration into this toolset.

- Cinema-player: Dolby, GDC, Qube and Barco (Barco S4 to be done),
- Projectors: NEC and Barco are in the works.
- Sound processors: JSD/QSC, Dolby are in the works.
- IO-control: RLY-8 and JNior are in the wortks.

This equipment supported is limited to that of which the developers have access to. If you would like your specific
equipment supported, please contact the developer to discuss. Typically access to the equipment will be needed. Remote
access is generally all that is needed.

# Reporting bugs and errors

Please utilise the github page and its issue tracker to report issues you may find.

# System Requirements

The recommended hardware and software requirements for Catcher are as follows.

## Hardware

Catcher is a server applications that performs many processes simultaneously and as such needs a modern computer that
runs Ubuntu-server (LINUX). A CPU with 4+ cores with Hyperthreading is recommended. 8Gig of Ram or better. The computer
can have the GUI activated but it is recommended that **NO** GUI is used. A dedicated computer/server is recommended.
The user accesses the system via a Web browser and so can be used from any computer terminal with a web browser. If GUI
is to be used 16 gig ram is recommended.

If using the LMS feature the system will be storing a large amount of data. The server needs to either have a large
amount of disk, or be in a position to mount a large amount of disk from a storage server. I recommend the following
when it comes to disks for the system.

- A 256-500 gig SSD system disk. This is the target for the operating system. SSD are very reliable, and having a RAID
  is not so important these days. However, over provision the disk ensures it will last a very long time due to how SSDs
  work and age. (500gig), Mirror/RAID of the system disk is also nice to have.
- 3 or more storage disks, 4gig or better. Really depends on how much data you want to store. 3 or more as so they can
  be RAIDed together using your prefered RAID solution. (I recommend utilising ZFS, or an external NAS system such as
  TrueNAS)

IF you just want to get started, I recommend utilising a single 10gig disk and install the operating
system on that disk, and use its extra space for storage. This avoids the need to implement RAID, however,
may be quite slow at some processes due to the lack of IO of a single disk.

## Software

The application is based on **docker** that containerised the application and all the services it needs.
Due to this, you can typically run the application on any **docker** capable server or instance, however,
the ability to ingest PHYSICAL disks and USBs is based on ubuntu server. Ubuntu Server 24.04 LTS is the
target operating system to run the catcher application. However, there is no reason you could not run
it virtualized and use a satellite PC that ftp/exports the mounted CRU-Disks/USB-sticks for ingesting.

**The installation process has gone though a significant update due to Ubuntu's implementation change for
docker from LTS 24.04**

<br/>Typically, when installing a system to run catcher on, you install be base ubuntu-server 24.04 LTS onto
a computer. Install docker-compose, then follow the installation procedure below.

## Who is expected to install this for cinema owners?

This is a difficult question. Cinema owners are businessmen and not IT professionals. However, I know
a lot of cinema owners who learn the toolset of running a small cinema, such as minimal maintenance of
projectors etc, as to keep costs down. Or utilise local IT skills (local computer support companies)
The same approach can be taken here.

Integrators and support agents that service cinemas are also more inclined to offer expensive tools
that come with 25% yearly maintenance costs they prefer to push as a source of income and stickiness
to the client. Many smaller cinemas cannot afford this and I would recommend cinema owners encourage
agents to be more ambidextrous and embrace certain free tools when suitable. Charging for labour
only when needed.

The platform for catcher is based on common open source technologies that cinemas should be able to
source reasonable local know how to implement. The local IT shop, or university student level is
the target level of expertise. I know many cinema owners that would be able to figure this out
themselves and enjoy the challenge of doing so.

The install path is:  Get suitable hardware, install "minimal" Ubuntu Server LTS, follow these
install instructions below.

# Firstly IMPORTANT to current users

Users who have already installed cinema-catcher-app are highly advised to perform an update to
the downloaded codebase. This is because the docker-compose.yml file has changed considerably to
deal with log file growth.

To do this, you simply need to goto the cinema-catcher-app directory, and as the root user,
run the following command:

```
docker compose down
git fetch origin main
git reset --hard origin/main
```

After doing that, I recommend upgrading to the most recent version by running the following
command:

```
bash update.sh
```

This script will stop the application, pull the latest code, run upgrade scripts, and restart
the application.

# How to install Catcher

## Ready your server

Before you continue, the server needs a number of items.

- Install your docker-capable server, recommended Ubuntu 24.04 LTS with minimal server install.
- Make the storage directory and mount your storage disk onto that directory.
- Network and IP address configuration.

### Mounting storage disk (If using for DCP asset storage)

You must make the following directories and mount your storage disk onto the directory.

```
sudo mkdir /opt/catcher
sudo mkdir /opt/catcher/storage
```

This is where some LINUX know-how comes in handy as the storage disk, be it a Hardware RAID,
software RAID under linux (ZFS recommended), or mounted from a storage server, the storage
disk must be mounted on the
`/opt/catcher/storage` directory. I recommend you google how this is done based on your
requirements.

If you are just taking the simple path and installed the Ubuntu-server onto a large disk,
just make the directories. If nothing is mounted on the `storage` directory, the files
will be stored on '/' or root filesystem, same as the operating system.

### Setup your network interfaces

It is recommended that the server has two physical Network interfaces. One on the
typical Internet connected network, and the second on the Projection/Media network. Many
cinemas keep the Projection network on a physically isolated network so it cannot
reach into the internet. As the catcher needs to talk to the projection network
devices and is also likely to pull content from the internet or send mail reports,
it will need two separate interfaces connections, one for each. NOTE: some smaller
cinemas, keep this all on the same physical network. This is simpler for them,
and if it works. It works, and is easier to manage. But in general, separate
physical networks are recommended.

The projection network requires a STATIC IP address as it needs to be referred
to in the `docker-compose.yml` file.

## Installing the software

As of Ubuntu 24.04 it is not recommend to use Docker that comes with Ubuntu as it
has been converted to a SNAP based install that does not allow suitable permissions
for the docker containers to work with the software.

It is recommend you follow the docker install from the docker website itself.
Found at https://docs.docker.com/engine/install/ubuntu/  Install docker using the `apt repositor` method.

Please read the docker documentation as linked above and follow its instructions. Once you have
completed the install, return to this install documentation and continue.

You now have the lastest docker installed, and can be checked with the command:

```
sudo docker --version
Docker version 20.10.22, build 3a2c30b
```

You should have the above version or greater.
`docker-compose` is now installed as part of docker and is no longer an extra install requirement.

### Other required tools

Git is required to download the Repository. To install it:

```
sudo apt install git
```

Now lets download the base `docker-compose.yml` file what describes to docker how to download and run the software. We
do this by cloning the files down from Github.

```
cd /opt
sudo git clone https://github.com/jamiegau/cinema-catcher-app.git
```

This will download the `docker-compose.yml` config file and other files into a directory
called `cinema-catcher-app` into your current directory that should be `/opt`. In this
directory you control the docker containers and bring up the application and all its
services. But before that can occur, you must setup some local variables.

## Create the configuration file.

Create a file called `.env` file is in the directory `/opt/cinema-catcher-app`.

```
cd /opt/cinema-catcher-app
sudo nano .env
```

`nano` is a basic text editor, but `vi` or whatever text editor you are comfortable with can be used.

Copy the following into the file:

```
LOCAL_TIMEZONE_NAME=                   # for example: Australia/Brisbane
CATCHER_HOSTNAME=                      # for example: CHAIN-SITE-catcher
EXPOSED_IP_PROJECTION_NETWORK=         # for example: you projection netwrok ip, ie: 192.168.1.100
IN_PRODUCTION=True
```

Update these three variables as described by their names. PLEASE REMOVE THE COMMENTS `#`
after updating with the correct values.

**It is very important you set a unique `CATCHER_HOSTNAME` in the `.env` file.**  It is recommended that
you use a name like `CHAIN-SITE-catcher`.

For example `vue-nederland-catcher` (For Chain: Vue. Location: Nederland) or `cc-ararat-catcher`
(For chain: Centre Cinemas. Location: Ararat).

`EXPOSED_IP_PROJECTION_NETWORK` is the static IP address you assigned to the network interface on
the projection network.

`IN_PRODUCTION` can be set to False, to enable debug logging in the application containers.
(See the `docker-compose.yml` file for more detail.)

Set the TIMEZONE_NAME environment variable. This should be set to, for example
`Melbourne/Australia` or the suitable name for your location. (
see https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for a list of names.)

Run the *.sh files by using the `bash` command while as root.

```
bash TAIL.sh
bash update.sh
bash start.sh
```

It is recommended that you start a ROOT bash shell when doing these commands.

```
sudo bash
Password: *********
root@CHAIN-SITE-catcher:/opt/cinema-catcher-app#
```

You can see you now have `root` in the prompt and a hash `#` at the end, indicating you are now
running as a root user. (Be careful)

### Download the software

Once you have created the local config file. Its time to pull down all the software from the docker-hub. To do this
type:

```
root@catcher-dev:/opt/cinema-catcher-app# docker compose pull
```

This will take some time as there is nealy 2GB of applications that will be downloaded. Get a coffee.

Once this has completed, type the next command to initialise the install (ie, the database etc.)

```
sudo docker compose run backend python3 ./manage.py migrate
sudo docker compose run backend python3 ./manage.py catcher_setup
```

And finally, start the server.

```
sudo docker compose up -d
```

You can now type the IP address of the Catcher Server into a browser and continue with the setup
of the software. If you reboot the server, the docker service should shutdown and restart
the docker containers automatically.

### Default Login

Once the system is running, you can go to the USER-INTERFACE by using your browser
and typing the IP address of the server you installed the cinema-catcher-app on to.
This will brig up a LOGIN-PROMPT. The default username and password is:

```
Username: admin
Password: admin
```

Once you login you can change the password and/or create users from
the **Admin -> Users** menu on the left of the interface.

### Other useful commands

To get the status of the containers.

```
sudo docker compose ps
```

To tail the logs of the docker containers.

In the same folder at the config file you will find the command `TAIL.sh`, use this command
to monitor the debug output of services. It will do all services if you ommit the service name.

To only tail the backend service:

```
sudo bash TAIL.sh backend
```

Shutdown the catcher server.

```
sudo docker-compose down
```

Update the server to latest version of the containers by using the `update.sh` script
It will shutdown, pull latest containers, update the database if required,
bring the catcher containers back up and delete any older container files left behind.
All in one command. NOTE: this is a good command to use to see if it frees up disk space.
The docker config is set to not fill your disk with logs and other files, but it still is
good practice to give it a clean now and then.

```
sudo bash update.sh
```

# Setting up the Software

In the near future a Video tutorial will be created.
For not, please refer to these other Manuals

General Catcher Manual [Click to Read](Manual.md)

AutoKDM Manual [Click to Read](Manual_AutoKDM.md), Note, a more complete manual is written into the application in the
menu system.
