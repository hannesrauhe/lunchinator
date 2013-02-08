#!/usr/bin/python

import time
import usb
import lunch_client

def findButton():
	for bus in usb.busses():
		for dev in bus.devices:
			if dev.idVendor == 0x1d34 and dev.idProduct == 0x000d:
				return dev

dev = findButton()
handle = dev.open()
interface = dev.configurations[0].interfaces[0][0]
endpoint = interface.endpoints[0]

try:
	handle.detachKernelDriver(interface)
except Exception, e:
	# It may already be unloaded.
	pass

handle.claimInterface(interface)

unbuffer = False
while 1:
	# USB setup packet. I think it's a USB HID SET_REPORT.
	result = handle.controlMsg(requestType=0x21, # OUT | CLASS | INTERFACE
	request= 0x09, # SET_REPORT
	value= 0x0200, # report type: OUTPUT
	buffer="\x00\x00\x00\x00\x00\x00\x00\x02")

	try:
		result = handle.interruptRead(endpoint.address, endpoint.maxPacketSize)
		if 22==result[0]:
			if not unbuffer:
				print "pressed"
				lunch_client.call("lunch panic")
			unbuffer = True
		else:
			unbuffer = False
		#print [hex(x) for x in result]
	except Exception, e:
		# Sometimes this fails. Unsure why.
		pass

	time.sleep(endpoint.interval * 0.001) # 10ms

handle.releaseInterface(interface)
