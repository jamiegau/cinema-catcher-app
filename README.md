# Catcher server for cinema exhibitors
## What is a catcher server?
As cinemas transition to an ever more IT centric way of operation, many aspects of running a cinema can be automated.  Catcher is a free to use tool that automates many aspects of running a cinema reducing the running costs.

This tool is focused on smaller cinemas, as some of the fetures are addressed in larger TMS system bigger operators would already utilise.  However, even larger cinemas may fine the ease of moving content around and a central autonomous LMS and KDM manager desirable.

## Who made the product and why?
The Catcher application was made by a small Australia company (https://www.digitall.net.au) that developes IP for operating autonomous cinema locations.  Due to the COVID crisis and the change in industry norms, such as "Streaming First" initiatives by the major exibutors and a reduction in windows from 90 to 45days, the result will be a reduction in attendance for cinemas as consumers change behaviour and take advantage of these offerings.  The objective for making part of the IP available under a free to use model is to ensure the culture of cinemas can matabolise these changes.  For example, if a small cinema looses 10-20% of attendance, but also drops its running costs by 10-20% by becoming more productive in operating the cinema, there is an overall 0 net gain.  Ensuring cinema is more likely to survive the changes occuring.

digitAll hopes this tool ensures many smaller cinemas can survive and thrive in these difficult times.

## What does Catcher do?
The objective of this application is for do the following:
- Operate as a LMS (Library Management Server), being a central storage of Films/DCPs as they arrive at your cinema.
- Allow ingest from CRU-Disks, USB-Disk, USB-Stick.
- Allow ingest from ftp sources such as is available from delivery devices that are being installed by major DCP-delivery-service providers.  i.e Deluxe, Motion Picture Solutios, etc. (There are numerous.)
- Auto ingest content as it arrives on digital platforms as listed above.
- Move DCPs between cinema locations via FTP.
- QC (Quality Check) all DCPs as they are ingested to ensure they are not corrupted or malformed.
- Automatically manage disk space and age content or delete content when needed. Users can override and protect content from deletion if required.
- Acts as a central location for all incoming content that ensures if a problem exists with content, the cinema opertor is informed of this on arrival. This ensures no last minute emergancies occur as problems are only aparent when a user attempts to utilise content.
- Automatically inspects an Email account for any KDM messages, downloads, unzips, and ingests KDM automatically. **Never have to deal with a KDM again.** NOTE: Dolby and Qube IMS are only supported at this time.
- Emails the cinema owners of all activity and specifially if a problem occurs as so the cinema operator can address it before it becomes an emergency.  For example, if a DCP coming into the cinema is corrupted in any way.

The catcher application is a set and forget tool.  Typically if everything is going well, you don't even need to log into its interface.

# Reporting bugs and errors
Please utilise the github page and its issue tracker to report issues you may find.

# System Requirements
The recommended hardware and software requirements for Catcher are as follows.
## Hardware
A resonable modern computer that runs Ubuntu-server (LINUX).  A CPU with 4+ cores with Hyperthreading is recommended.  8Gig of Ram or better.  The computer can have the GUI activated but it is recommened that **no** GUI is used and you access the system vie a Web browser only. If GUI is to be used 16gig ram is recommneded.

As this is a LMS and will be storing a large amount of data, the server needs to either have a large amount of disk, or be in a position to mount a large amount of disk from a storage server.  I recommend the following when it comes to disks for the system.
- A 256-500gig SSD system disk.  This is the target for the operating system.  SSD are very reliable, and having a RAID is not so important these days.  However, over provision the disk ensures it will last a very long time due to how SSD's work and age. (500gig)
- 3 or more storage disks, 4gig or better.  Really depends on how much data you want to store.  3 or more as so they can be raided together using you  prefered RAID solution. (I recomend utilising zfs)

IF you just want to get started, I recommend utilising a single 10gig disk and install the operating system on that disk, and use its extra space for storage.  This avoid the need to implement RAID, however, may be quite slow at some processes due to the lack of IO of a single disk.

## Software
The application is based on **docker** that containerises the application and all the services it needs.  Due to this, you can typically run the application on any **docker** capable server or instance, however, the ability to ingest PYSICAL disks and USBs is based on ubuntu server.  Ubuntu Server 20.04 LTS is the target operating system to run the catcher application.  However, there is no reason you could not run it vertualised and use a satalite PC that ftp/exports the mounted CRU-Disks/USB-sticks for ingesting.

Typically, when installing a system to run catcher on, you install be base ubuntu-server20.04 onto a computer.  Install docker-compose, then follow the install procedure below.

## Who is expected to install this for cinema owners?
This is a difficult question.  Cinema owners are businessmen and not IT professionals.  Agents that service cinemas are also more enclined to offer expensive tools that come with 25% yearly mentenace costs.  Many smaller cinemas cannot afford this.

The platform for catcher is based on common open source technologies that cinemas should be able to source resonable local know how to implement.  The local IT shop, or High-School student level is the target level of expertise.  I know many cinema owners that would be able to figure this out themselves and anjoy the challenge of doing so.

The install path is:  Get suitable hardware, install Ubuntu Server, follow these install instructions below.

# How to install Catcher
After installing Ubuntu Server 20.04 LTS, when the computer is ready, you will get a black text only screen with as `login:` prompt.  Login as the user you setup when installing Ubuntu.  This will result in the command prompt.
```

```

