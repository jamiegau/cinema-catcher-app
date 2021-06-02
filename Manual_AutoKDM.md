Overview
========

AutoKDM is used to automate the download and ingest of KDMs (Key Delivery Messages that unlock encrypted content). AutoKDM does this by doing the following:

-   Logging into an Email account that receives KDMs. This is performed every hour. (Note: this can also be supported in real time by implementing your own Email server.)
-   Downloading all messages and attachments to look for KDMs.
-   All KDMs are placed into a Database.
-   The system then looks for all KDMs that have not been pushed into registered SMS/DCI-Player or TMS server. These KDMs are then pushes into those registered devices.
-   It will then optionally Email the SMS/DCI-Player owner that a KDM has been delivered.
-   Projection will be emailed if any issues occur, such as unable to contact SMS/DCI-Player, or received a KDM for a non-registered SMS/DCI-Player.
-   AutoKDM logs exactly when a KDM arrives and when it is ingested.
-   The system will automatically delete KDMs/history after 3 months from KDM-finish-date.

Setting up AutoKDM
==================

To setup AutoKDM, you must configure the following:

-   One or more Email accounts to monitor using the IMAP protocol (an Email sync and retrieval protocol). Note: gmail and other accounts may need to have security setting changed to allow this. Please see [Allowing less secure apps to access your Gmail account](https://support.google.com/accounts/answer/6010255?hl=en) To set up Email sources please go the ["AutoKDM/Sources"](http://10.30.1.3/app/#!/kdm/sources) page.
-   One or more target SMS/DCI-players must also be setup as targets for incoming KDMs. Please see the ["AutoKDM/Targets"](http://10.30.1.3/app/#/kdm/targets) page

Menu walk through
=================

AutoKDM is made up of 3 configuration pages. Simply follow them in order, filling out the needed information to get AutoKDM to start working for you.

Menu- AutoKDM/Sources
---------------------

In this section you must set up the source Email accounts that the AutoKDM application will monitor. Each hour the system will log into the configured accounts and download all Emails. It will then check them for attachments and extract any files it finds. If there are any zip files, it will unzip those files and search for KDMs in the XML files it finds. When a KDM is found, it is added to a database.

First you must **[Add]** a new email source by clicking on the **[Add]** button along the top of the page. This will bring up a dialog asking for the hostname or IP address of the IMAP email server. (Note: this can be edited later). Once you create the new item. find and select it on the table. Below the table all the options you must configure will appear.

Click the **[Edit]** button so you can change the options. From here, you must make sure **IMAP-Host, Username** and **Password** are correct. It is also a good idea to give the entry a description as it may help later.

Once you are happy with your settings, select the **[Test]** button. You will get either a **GREEN** popup, indicating all is well, or a **RED** error with a description to help diagnose the cause.

The **[Fetch]** button will connect to the specific selected Email account immediately. If any KDMs are found, it will ad them to the Database. It will then immediately attempt to deliver any outstanding KDMs that have not been delivered.

The **[Fetch All]** button along the top acts as a manual override and will perform the full hourly check of all Email sources and attempt to deliver/ingest any KDMs that have not yet been delivered.

Menu - AutoKDM/Targets
----------------------

In this section you must set up the target SMS/DCI-Player meta-data. For AutoKDM to figure out what to do with a KDM it needs to have an understanding of the SMS/DCI-Player in use in your cinema. On this page you must enter the DCI-Player types, serial numbers, and supply the Public Certificate as a way for the AutoKDM system to figure this out.

Click on the **[Add]** button to add a new blank entry for a DCI-Player. This will ask you to enter an IP address for the DCI-Player (Note: This can be changed later). Once a new entry is created, find and select that new entry. The following configuration options must then be set to allow correct operation.

-   **IP Address:** Depending on if you are pushing the KDM directly into the SMS/DCI-Player or FTPing it into a TMS, this must be the IP address of the DCI-Player of TMS server.
-   **Delivery Method:** this option may be the following: **Direct**-directly into the SMS/DCI-Player, **FTP**-Ftp into a specific location on a server, typically the TMS, **Ignore**-Ignore this item. If a KDM comes in addressed to this identity, simply ignore it. (This is unfortunately needed as distributors often get data mixed up and can send you unneeded KDMs.\
    AutoKDM currently supports the following direct SMS/DCI-Player ingest APIs: Dolby/Doremi-(yes), Qube-(yes), Barco-(coming), GDC-(No), Sony-(no) Christie-(No)
-   **FTP Username, Password and Path**: these items will show if the delivery method is FTP. You can set and test these options by using these fields.
-   **Serial:** This is of major importance. As it prescribes the identity of the SMS/DCI-Player. Based on this, AutoKDM can figure out where a KDM must go. It is extremely important you have the Serial numbers of your SMS/DCI-Players and that they are correct.
-   **Location:** You must fill this out with a description of the location of the projector (For example: CinemaNam-C1", as it is associated with the KDMs and allows you to easily see what KDM is targeting what screen/SMS/DCI-Player. This is shown n the KDMs menu.)
-   **Type:** Along with the Serial, you need to tell the system what Vendor the SMS/DCI-Player comes from. As this us used to lookup the Public certificate in the next section.
-   **CommonName(CN):** This is the actual certificate identification string that is used in the X509 identification portion of the certificate. The serial number and much more can be contained in this key field. This makes it a difficult field to figure out. Typically this field is automatically worked out via the Public certificate that you can automatically fetch in the following options. However, if need be, you can still hand edit this field (For advanced users).
-   **Player Cert:** This is a copy of the text contained in the Player Certificate. This is what is used when a KDM is being created for that specific SMS/DCI-Player. In this case we are using it to extract the X509 identification so we can match it up to the certificates. This text area can have the TEXT of the Certificate pasted in, but typically its easier to use the automatic tools under the "Get Cert" buttons.
-   **Get Cert:** To make it easy to obtain the certificates, there are two methods to retrieve them. The **[From Player Direct]** button will attempt to contact the SMS/DCI-Player directly (NOTE: the AutoKDM server will need direct connectivity to the projection network and as such the SMS/DCI-Player.) When this button is clicked, it will attempt to retrieve the public certificate of the SMS/DCI-Player directly from the player. It will then load the Certificate text into the "Player Cert:" followed by extracting the "CommonName(CN)" into the field above that. This will happen automatically.\
    The **[from Vendor FTP]** button will, based on the serial number and vendor data, contact Internet databases of SMS/DCI-Player Certs. And again, fill out the "Player Cert" and "CommonName(CN)" options above automatically.\
    **NOTE: These features are not always available depending on vendor and network availability.**
-   **Contact Name:** The name of the person to contact for ingest and error reports.
-   **Contact Email:** The Email of the person to contact for ingest and error reports.\
    **Note: this must be correctly set if you are to receive Email when KDMs are ingested or any form of Error occurs.**
-   **Inform On Ingest:** If enabled, when a KDM is ingested directly into a SMS/DCI-Player, or FTPed to a FTP repository (TMS), the user above will be Emailed a report.
-   **Warn After Mins:** is a length of time to wait before sending a warning if a KDM fails to ingest into a target SMS/DCI-Player of FTP server. As many locations turn equipment of at night, a grace period is set here so an error does not occur. Typically in the morning, the equipment will be turned on and the KDM will be delivered before the time period runs out.

Menu - AutoKDM/KDMs
-------------------

This page contains the database table of all KDMs ingested into the AutoKDM system. From here you can easily search for a KDM for a specific film that targets a specific screen by typing into the search fields at the top of each column. This is especially helpful if you want to quickly find out if a KDM has been sent or not for a specific film on a specific screen.

The table also shows when a KDM was received, the dates it is valid, and the date/time it was ingested into the target SMS/DCI-Player.

When selecting a specific KDM entry, you will see more detailed meta data on that KDM below the table. This is helpful if you need to diagnose issues such as targeting incorrect CPL-UUID combinations.

On the Detail screen, you can also set the **Delivered Flag** back to false as to force re-delivery of a KDM. For example, you could search for all KDMs for a specific screen, click on each and set the delivery back to **False**, click **[Deliver NOW]** and immediately force a re-delivery of those KDMs. (For example a SMS/DCI-Player fault and system disk replacement needed all KDMs to be re-ingested.)

Network Connectivity Requirements
=================================

For AutoKDM to delivery KDMs directly into SMS/DCI-Player, the AutoKDM server will need direct network access to all SMS/DCI-Players. If only pushing KDMs to a TMS, the AutoKDM server will need to deliver KDM directly to that TMS server over the network. Security considerations should be considered under each scenario.

When using AutoKDM, we highly advise that physically separate networks are used for each network (Internet-network, and projection network), meaning the AutoKDM server should have two network connections. One for each physical network.

Real Time AutoKDM Ingest
========================

Tipically the AutoKDM system will contact a IMAP email server hourly to check for KDMs. However, it is also possible to have Email piped directly into AutoKDM and have them ingested as soon as they arrive as an Email. Typically it will take under 2 mins from the time the Email is SEND to when it hits the SMS/DCI-Player. This is a great feature for when something goes wrong and you are waiting for an Emergency KDM to arrive. It will appear in your Email, then 30 seconds later you will get an Email that it has been automatically Ingested. Emergency avoided.

### Implementing Real Time AutoKDM Ingest

The recommended method for implementing this feature is to have your IMAP email account automatically forward all Email to a internal Email server that will push the Email directly into the AutoKDM server. This ensures that if something did go wrong with your internal Email server, AutoKDM will still pick up the Email on its hourly check.

Implementing your own internal Email server is quite involved and an IT support person is recommended. However, in a broad description we recommend the following.

-   A DNS name server for a domain that the Email address will live in needs the following: A DNS-A-Record mapping the server IP (Or external Internet IP you would port forward port 25, SMTP to the internal Email server). A DNS-MX (Mail Exchange) record specifying the active email domain will need to be delivered to the above specified IP address. This will allow the Email server to receive Emails.
-   A Ubuntu or similar Linux based Email server is setup that is configured to accept Email under the domain configured above. Typically using postfix email agent.
-   The Email server will need to redirect the RAW email into a special web end point on the AutoKDM server. This endpoint is:\
    **https://AutoKDM.IP.address/api/KdmApp/IncomingKDM/**\
    Typically under linux and the postfix mail server, the /etc/aliases file needs the following configuration line to enable this:\
    **AutoKDM: "| curl -H \"Content-Type: application/json\" -X POST --data-binary @- https://AutoKDM.IP.address/api/KdmApp/IncomingKDM/"**

This configuration will pipe the RAW email being received at AutoKDM@domain.for.internal.email.server.com into the AutoKDM real time ingest API.

If you need help with this it is recommended that you hire a knowledgeable engineer, such as James Gardiner himself as he wrote this software.

**NOTE: It is possible to have the AutoKDM server also act as the Email server. For example setting up a docker container as part of the docker-compose.yml file is suggested.**

