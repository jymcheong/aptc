## Installation steps for MISP host
1. git clone https://github.com/jymcheong/aptc.git
2. Edit <path to misp app>/Controller/EventsController.php
3. Locate addTag method, towards the end of the method, find $this->Event->save($event) & add
```
if ($tag['Tag']['name']=="aptc:test-start") shell_exec("python3 /var/www/MISP/tools/aptc/getpayloads.py -id ".$id." > /dev/null 2>/dev/null &");
```
4. Create aptc folder under MISP tools directory 
5. Copy all the aptc scripts to that folder & adjust permission accordingly
6. Edit key.py to set misp_url & key
7. Create target paths (samba mount point) to write payloads to (give appropriate permissions for read/write)
8. Install Samba & setup share for targets to mount (by default APTC writes to /opt/aptc/targets/HOSTNAME. Read https://automated-payload-test-controller.github.io to understand how this whole thing works)

## Installation steps for Windows target(s)
1. Mount the samba shared folder in your Windoze
2. Copy filemonitor.vbs to the target(s), make it auto-run upon login (target should [auto-login](https://technet.microsoft.com/en-us/library/ee872306.aspx))

## Synopsis

A set of scripts using [PyMISP](https://github.com/MISP/PyMISP) to extend [MISP](https://github.com/MISP/MISP) for automated payload testing.

[User Documentation](https://automated-payload-test-controller.github.io)

[Demo of CVE2017-0199 payload youtube link](https://www.youtube.com/watch?v=mASJv_2HZbM)

## Sh0ut 0utz
Big thank you to the awesome folks @ https://gitter.im/MISP/MISP & Harvard-IT-security

## Useful links
Most convenient way to setup the latest MISP: https://github.com/harvard-itsecurity/docker-misp
