# GR-GSM based TMSI sniffer
This is just the proof of concept code for MSISDN -> TMSI mapping.
The algorithm is very simple and was already described in the past.

#### Terms of use
This code is distributed in hope, that it may be helpful for someone, who is learning mobile communications. I am not responsible for possible damage, caused by someone using this software. Please, use it for research and/or education purposes only.

#### The algorithm
1. Allocate a new array for further recording;
2. Start recording, adding every TMSI into the allocated array;
3. Cause a Paging Request for the victim's phone (call, SMS);
4. Stop recording;
5. Repeat above steps, until we get one TMSI, which can be found in all recorded arrays.

#### Possible difficulties
- TMSI Reallocation. In some networks it happens very rarely, so you can call someone, send an SMS, reboot your phone, and TMSI will be the same as before. Other networks change TMSI after a fixed number of connections. Some networks change TMSI for every dedicated connection, and in this case this toolkit is useless.
- Subscriber notifications. What would you think, if someone call you (or send SMS) multiple times? Something strange and fishily, right? So, instead of calling or sending short messages, it is possible to cause a Paging Request without subscriber notification. One way is to use silent/broken SMS. Another way is to initiate a call to the victim and hangup before the phone will ring.
