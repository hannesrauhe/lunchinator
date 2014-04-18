#Cold Start
Lunchinator does not know any peers.

* Someone else enters your hostname/IP to his list of peers
    * The other Lunchinator sends you a `DICT` message with its list of peers
    * You do a regular startup
* You add the hostname/IP of someone else into your list of peers
    * __??__

#Regular Startup
Lunchinator already has a list of peers from its last run.

* It sends `REQUEST_INFO` to each peer in its list (peers now know my information)
* The peers answer with `INFO`, I now know their information

# Messages

Message | Contents | Sent when | Reason | Sent to | Received from
--------|----------|-----------|---------|-------|-----
`REQUEST_INFO` | Info dictionary | On startup | Peer detection, info aquisition | Every peer | Everyone
`REQUEST_INFO` | Info dictionary | I see someone I don't know (__??__) | Info aquisition | Unknown peer | Everyone
`REQUEST_INFO` | Info dictionary | I change my group (__is this necessary?__) | Info aquisition | Everyone | Everyone
`INFO` | Info dictionary | As answer to `REQUEST_INFO` | Someone asked me ;-) | Sender of request | Sender
`INFO` | Info dictionary | When the info dictionary changes | Inform others about changes | Every peer | Everyone
`REQUEST_DICT` | __??__ | Regularly | Update list of active peers (safety) | Random member | Members
`DICT` | Peers dictionary | Answer to `REQUEST_DICT` | Someone asked me | Sender of request | Members __??__
`DICT` | Peers dictionary | I add a new member manually | Tell the member the peers | New member | Members __??__
`LEAVE` | _??_ | Server stops | Others remove me from their peers | Everyone __??__ | Everyone __??__
`LEAVE`| __??__ | I change my group | Seems like restart to others (__is this necessary? couldn't group change be handled in info dict update?__) | Everyone __??__ | Everyone __??__
`<empty>` | Nickname | Regularly | Ping | Everyone | Everyone
