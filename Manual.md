Catcher Manual
--------------

Welcome to the D-Cine.net Media Asset Catcher (catch-server). This server is used as a repository and control system for content arriving at your cinema via network delivery over the internet or ingest from physical disks and USB sticks. Depending on how you operate, the catch-server supports different methods for operators to allow the retrieval of content. These include:

-   The catch server acts as a Library Management Server (LMS), allowing you to ingest DCPs to SMS/DCI-Players directly from the SMS/DCI-Player interface
-   Automatically/On-demand push of DCPs into a TMS or a ftp upload folder
-   Automated monitoring of service entity download boxes
-   All ingested content is verified for errors and detection of playback errors
-   Allows early warning of any faults in DCPs ensuring operators have more time to rectify faults
-   Common FTP server access
-   AutoKDM, Automatic KDM download and push into DCI-Players
-   AutoDelete, media assets can be marked as protected otherwise, oldest assets will be deleted as requied.

For more information, please keep reading for a more details explanation of each and how to use them.

Online Portal and advanced Quality Check and centralised download platform
--------------------------------------------------------------------------

An online portal is also available at "[admin.d-cine.net](http://admin.d-cine.net/)". Access to the portal must be arranged through D-Cine.net Support. Please contact them for account/login creation.

The Catcher software is self contained and access to the online portal is not required. However some additional features may dpend on the centralised Database. For example, looking up what DCP is associated with what film.

The portal supplies the following additional features and capabilities:

-   Media Asset QA (Quality Assurance)
-   Audio loudness statistics
-   Waveform and channel display
-   Proxy and full quality eCinema Preview.
-   Download of full quality eCinema version
-   Backup Repository/Download of all Media Assets/DCPs assigned to your locations
-   Enterprise level overview of all sites under your control

Network Requirements and Security
---------------------------------

The catch-server requires network connectivity to the internet and projection room equipment for operation. Due to limitations by certain Integration entities, the ability to transfer DCPs between devices can be restricted. With the VPF over, this should no longer be an issue, however, some integrators are very restrictive and should be avoided.

D-Cine.net utilises best practices in security and has over 10 years of experience in content protection and encryption.

Network Utilisation
-------------------

The catch-server is designed to utilise pre-existing internet connectivity and to operate in the background without being noticed. This is done by setting bandwidth limits that the catch-server will utilise at different times of the day to ensure it does not effect general internet usage and speeds. Please see the [Config] menu for setting speeds and time of day the speeds will take effect.

To help with diagnosing any bandwidth problems, there is a tool under [Status] -> [Bandwidth] that can be used to monitor the utilisation of the internet connected interface.

Accessing Media Assets
----------------------

When a Media Asset arrives, you can set the system to Email the admin users with the result of the verification of the DCP. The next step is to make the media asset available to your projection infrastructure. Media assets (DCPs) can be accessed by FTP protocol. This section will cover the protocols and common methods used to access the DCPs via these protocols.

A brief list of common methods used to access Media Assets (DCPs):

-   Automatic push into TMS
-   FTP direct access or as LMS ingest into SMS/DCI-Player

### Automatic Push into Theatre Management System

If you have a TMS the user can automate of manually trigger FTP push of DCPs directly into your Theatre Management System (TMS). This is a set and forget configuration as typically content, on arrival, will be pushed into your TMS. The content on the catch-server will auto delete based on age and disk space.

### FTP server and LMS

The catch-server also acts as an FTP server. An FTP (File Transfer Protocol) server can be used in many different ways. The most common use of FTP is as a Library Management System (LMS). All SMS/DCI-Players use FTP to copy DCPs from a TMS/LMS onto its local storage. The catch-server performs as a LMS allowing SMS/DCI-Players to pull content over the network from them as if they were a USB-Disk or CRU-Disk/Hard drive. Please see your SMS/DCI-Player manual on how to set up external FTP/LSM asset sources.

The Catch-Server can be connected to via an ftp-client. We recommend using a common/free FTP-Client applications tool called [filezilla](https://filezilla-project.org/download.php) available on Windows/Mac/Linux. With this tool you can connect to the catch-server by ftping into the catch-server IP-address and using the login: media and password: media

### FTP directory structure

The catch-server breaks up content into directories based on type. This is to allow users to mount only the type of content they require. For example, a SMS/DCI-Player may have an ingest source that points at only "trailer" Trailer content as apposed to "advertisement" Advertisement content. A directory called "all" also exists that contains links to ALL content ingested into the server.

Due to this, the exported FTP file share root directory will have the following directories.

-   all - all content of every type
-   trailer - only trailer media assets (DCPs)
-   advertisement - only advertisement media assets (DCPs)
-   And other common DCP/CPL ContentKind classifications

Notifications
=============

When a Media Asset arrives, you can optionally have an Email sent reporting the arrival of an Asset. Please see the Config page to setup this option.

Installation Considerations
===========================

When the catch-server is installed, it typically consists of a enterprise level server. This is to ensure reliability and ease of support. The server can be located anywhere but is typically installed near the TMS or main network switch as it will require connectivity to the TMS/projection network to allow direct push or pull of Media Assets into SMS/DCI-Players or the TMS.

When installed, the unit is connected to the required networks and powered on. All other control is done by the Web based front end.

### Network Connections

The suggested install is to have the catch-server use two independent physical connections.\
**Port-1** to the Internet connected network, utilising DHCP to automatically gain access to the Internet and control server that sends content to the catch-server.\
**Port-2** for a secure physical connection to the projection network or directly to the TMS. This allows for an isolated network segment from the catch-server to the projection network to ensure the greatest possible security. Traffic from the Internet connected network will not be aloud to pass through to the projection/TMS network keeping them physically separate but allowing the catch-server to communicate with both.

As this topic is very much dependant on the topology of the networks at your location, we suggest you contact your integrator for a more details discussion.

### Local Network IP

When installed, the support agent will work with the location in selecting STATIC, non-changing IPs that can be used to communicate with the catch-server. Typically this is done for both the front of house internet side and the projection network/TMS side. If you have misplaced or lost these Static IPs, please contact support as they have a record of these settings.\
**Note:** we commonly use the IP X.X.X.246 as the internet side IP. If your front of house network uses a common C-Class subnet of 192.168.0.X, typically we would place the catch-server on 192.168.0.246. 246 is high on the IP range and rarely used and is found to be free in nearly all cases.

Full Manual
===========

The Catch-Server is designed to operate with as little intervention as possible. Once setup, it is a set-and-forget type affair. As such, the following detailed manual will help those who may come back to occasionally change the configuration, such as to change a target Email report.

Control Menu walk through
-------------------------

The left hand side of the Web-interface consists of a menu. This menu is were you navigate the software and access settings and media assets. In this section of the manual we will go through each menu, what it is for and how to set it.

### MENU - Dashboard

The Dashboard is an informative page that displays a summary of assets and other information.

### MENU - Profile

The Profile menu is the location were you can edit details about the logged in user. This consists of name and **most importantly, the EMAIL-ADDRESS**. The Email address is important as it is the address used to inform the projection staff of events and errors.

### MENU - Config

This page is the main configuration portion of the catch-server. It is were key configuration items must be set up correctly for operation.\
The items can only be changed after clicking the **[Edit]** button and will only take effect when the **[Save]** button is clicked.

### MENU - Config - Control Server/API-Key

This is an optional setup that connects the catch-server with a larger server that acts as a database lookup system and centrol control portal for entities to distribute assets.

### MENU - Config - Bandwidth Utilisation

These options are used to control how much of the internet link the catch-server may utilise. This involves selecting two different times of the day, and download speeds limits that apply during that part of the day.

These options allow the user to setup a day-time speed and a night-time speed. During the day it is expected that other users would be using the internet so a low and slow speed will be set to ensure it does not interfere with day to day internet use. While during the night, the catch-server will be let loose to utilise most of the capability of the internet link.

### MENU - Config - TMS Integration

To enable the automatic push of media assets directly into your TMS, (so they magically just appear in your TMS list of Assets) you must setup this section of the configuration.

After enabling, a number of options will appear. These options setup the automatic FTP upload parameters. These options will typically be supplied to you by the technician setting up the TMS. The TMS typically needs auto ingest features enabled before this will operate correctly. (Please contact your TMS administrator or support agent to ensure these features are enabled) The ftp upload ip-address, login, password, and destination path will need to have been setup. Once you have these parameters, you can set them here. Use the **[Test TMS Configration]** button to test the configuration is correct.

When the "**TMS Auto Push**" on/off toggle button is enabled, the system will automatically push arriving assets into the TMS. If disabled, the assets will not automatically be pushed. One the [MENU-MediaAssets] page where media assets are listed, there is a button you can select to push the assets on command. In effect this enables automatic or manual push of media assets into the TMS.

The "**TMS Ping Test**" on/off toggle button is used to enable or disable the system using a ping test to check if the TMS is there before attempting the FTP push. As some Integrators implement over ambitious security, blocking ICMP packets (Pink Packets) this test will fail. This option disables this test.

### MENU - Config - Email Notifications

The Catch-server utilises Email for sending reports to the projection staff. To do this it needs to be able to SEND EMAIL.

The Catch Server can utilise numerous common Email services for sending Email. Here I will cover two of the most common methods.

Method 1, an open relay agent. This typically means you have a Mail server on your network that will allow relaying of Emails coming from a known IP address. In this case, the only options that need setting are "**Hostname**" and "**Port**". (**TLS** must be disabled) Hostname of the open relay Email server, and port it listens on, typically port 25.

Method 2, Google gmail.com email account. As google offers free Email accounts, many users set up a gmail account specifically for sending Emails. For example, creating a gmail account with the email, "cinema.name@gmail.com". This account is then used for sending Emails.\
**NOTE:** for this to work correctly, you need to enable insecure login for the gmail account.

Once this is done, the typical options for using a Gmail account are:

-   Hostname: smtp.gmail.com
-   Port: 587
-   Username: cinema.name.autokam@gmail.com
-   Password: Password for gmail account
-   TLS: Enabled

"**Notification**" on/off toggle enables/disables notifications.

### MENU - Status

The Status menu is used to monitor the activity of the catch-server.

### MENU - Status - Status

This menu includes two tables. Table 1 is the status of tasks the catch-server performs. Typically this is used to see the current state of background processors. For example, communication to a server may be producing an error, this will show you the status of the last attempted communication.

### MENU - Status - Bandwidth

This screen will show you a graph of the bandwidth utilised by the main network interface. This is useful for seeing how much network traffic the catch-server is utilising in real time or over the last hour. It is a diagnostic tool that is useful if there is network issues and a technician would like to see what the catch-server has been up to.

### MENU - MediaAssets

This screen has a table of media assets (DCPs) available on the catch-server. From here you can select an asset and perform the following tasks:

-   Delete a media asset from the catch-server
-   Manually push a media asset into a TMS (If TMS integration is configured)

### MENU - Transfers

This screen lists two different queues.

The first queue is the download queue for the catch-server. The server will download two assets at the same time. If more then two items are in the queue, they will be listed here. (Future Feature, adjust order of download queue)

The second list is the finished download queue. This will also list errors and other issues that may have occurred during download.

### MENU - Logout

This screen allows the user to logout of the system forcing the user to login next time he returns to the page. Currently, once a user logs in, the login will stay current for many hours after the last interaction with the server. (i.e. if you return to the server login will not be required until this timeout occurs.)

Dealing with highly secure projection networks
==============================================

The security requirements at your cinema may vary in restrictions. In this section I will cover how to deal with different levels of restrictive security on the projection network. Due to security restrictions certain features are not supported as without network connectivity, the catch-server cannot perform some tasks. In this section, I will cover the three common levels of projection network security and the features they affect.

Low security
------------

This is equivalent to a office network level of security. This is the most common for smaller independents. In this level, there is no active security practices. However, it is **highly advised** that at the very least the front of house Internet accessible network and the projection network are placed on physically separate networks, however this is not required.

In this scenario, all equipment has the ability to talk to all other equipment. This allows for all features possible via the catch-server. For example, the catch-server would be on the projection network and act as a LMS, allowing every SMS/DCI-Player to ingest content directly from the catch-server as if it were just a USB-stick being plugged into the SMS/DCI-Player.

Also, the ability to automatically push into the TMS would also be possible, if the TMS is configured to accommodate this process.

TMS only connectivity
---------------------

In this case, the catch-server in networked with the front of house internet and TMS ONLY. This restricts communication to SMS/DCI-Players/Projectors. Everything must go via the TMS. In this case the main options is to setup the TMS to allow auto Push into the TMS or one way SMB/FTP share to the TMS. If using one way, only allowing connections going out from the TMS, the TMS operator would need to manually FTP or connect to the SMB share to transfer DCPs into the TMS and then onto the SMS/DCI-Players.

Full projection network restrictions
------------------------------------

In this case there is no physical way to connect the catch-server to the TMS or projection network. The only way to get media assets into the projection network is via USB device such as a USB-stick or USB hard drive. If this is your only option, the recommended method is to ftp into the catch-server and download the DCPs via the Filezilla application. Place the downloaded files onto a USB device then plug it directly into the TMS or SMS/DCI-Player to ingest the DCP.
