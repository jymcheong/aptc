## Installation steps on MISP host
1. git clone 
2. edit <path to misp app>/Controller/EventsController.php
3. locate addTag method
4. towards the end of the method, find $this->Event->save($event) & add
```
if ($tag['Tag']['name']=="aptc:test-start") shell_exec("python3 /var/www/MISP/tools/aptc/getpayloads.py -id ".$id." > /dev/null 2>/dev/null &");
```
5. create aptc folder under MISP tools directory 
6. copy all the aptc scripts to that folder & adjust permission accordingly
7. edit key.py to set misp_url & key
8. create target paths (samba mount point) to write payloads to (chmod 777 those directories because target VM script need to delete the payload)
9. install Samba & setup share for targets to mount

## Synopsis

A set of scripts using PyMISP (https://github.com/MISP/PyMISP) to extend MISP (https://github.com/MISP/MISP) for automated payload testing.

[More details](https://automated-payload-test-controller.github.io)

[Demo youtube link](https://www.youtube.com/watch?v=mASJv_2HZbM)

