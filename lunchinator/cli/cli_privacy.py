from lunchinator.cli import LunchCLIModule
from lunchinator import get_peers
from lunchinator.peer_actions.peer_actions_singleton import PeerActions
from lunchinator.privacy.privacy_settings import PrivacySettings
from lunchinator.log.logging_func import loggingFunc

class CLIPrivacyHandling(LunchCLIModule):
    def __getPrivacyPolicyDescription(self, policy):
        if policy == PrivacySettings.POLICY_EVERYBODY:
            return "Everybody"
        if policy == PrivacySettings.POLICY_EVERYBODY_EX:
            return "Blacklist"
        if policy == PrivacySettings.POLICY_NOBODY:
            return "Nobody"
        if policy == PrivacySettings.POLICY_NOBODY_EX:
            return "Whitelist"
        if policy == PrivacySettings.POLICY_BY_CATEGORY:
            return "By Category"
        
    def __getPolicyFromText(self, t):
        t = t.lower()
        if t == u"everybody":
            return PrivacySettings.POLICY_EVERYBODY
        if t == u"blacklist":
            return PrivacySettings.POLICY_EVERYBODY_EX
        if t == u"nobody":
            return PrivacySettings.POLICY_NOBODY
        if t == u"whitelist":
            return PrivacySettings.POLICY_NOBODY_EX
        if t == u"category" or t == u"by category":
            return PrivacySettings.POLICY_BY_CATEGORY
        return None
    
    def __getStateDescription(self, state):
        if state == PrivacySettings.STATE_BLOCKED:
            return u"deny"
        if state == PrivacySettings.STATE_FREE:
            return u"accept"
        if state == PrivacySettings.STATE_CONFIRM:
            return u"deny (ask if possible)"
        if state == PrivacySettings.STATE_UNKNOWN:
            return u"unknown"
    
    def __getPeerIDs(self, peer):
        if get_peers().isPeerID(pID=peer):
            return peer
        return get_peers().getPeerIDsByName(peer, sensitive=False)
        
    def __getState(self, text, policy):
        text = text.lower()
        if text in (u"allow", u"free"):
            return 0 if policy == PrivacySettings.POLICY_EVERYBODY_EX else 1
        if text in (u"deny", u"block", u"blocked"):
            return 1 if policy == PrivacySettings.POLICY_EVERYBODY_EX else 0
        if text in (u"default", u"unknown"):
            return -1
        if text in (u"yes", u"true", u"on"):
            return 1
        if text in (u"no", u"false", u"off"):
            return 0
    
    def __printExceptions(self, action, category, policy):
        exceptions = action.getExceptions(policy, category)
        if not exceptions:
            print "No exceptions."
        else:
            print "Exceptions:"
            self.appendOutput(u"Peer", u"State")
            self.appendSeparator()
            for peerID, state in exceptions.iteritems():
                peerName = get_peers().getDisplayedPeerName(pID=peerID)
                if peerName is None:
                    peerName = peerID
                    
                allow = (state == 0) if policy == PrivacySettings.POLICY_EVERYBODY_EX else (state == 1)
                self.appendOutput(peerName, u"allow" if allow else u"deny")
            self.flushOutput()
    
    def listActions(self, args):
        if len(args) == 0:
            self.appendOutput(u"Plugin Name", u"Action Name", u"Policy")
            self.appendSeparator()
            for dPluginName, actions in PeerActions.get().getAllPeerActions().iteritems():
                for action in actions:
                    if action.getMessagePrefix() is None:
                        continue
                    if action.getPluginObject() is not None:
                        pluginName =  action.getPluginObject().get_displayed_name()
                    else:
                        pluginName = dPluginName
                    self.appendOutput(pluginName,
                                      action.getName(),
                                      self.__getPrivacyPolicyDescription(action.getPrivacyPolicy()))
            self.flushOutput()
           
    def __getPluginName(self, pluginName):
        actionsDict = PeerActions.get().getAllPeerActions()
        
        pluginName = pluginName.lower()
        for aPluginName, actions in actionsDict.iteritems():
            # prefer displayed plugin name
            pluginObject = actions[0].getPluginObject()
            if pluginObject is not None and pluginObject.get_displayed_name().lower() == pluginName:
                pluginName = aPluginName
                break 
            
            if pluginName == aPluginName.lower():
                pluginName = aPluginName
                break
        if pluginName not in actionsDict:
            return None
        return pluginName
            
    def handleSetting(self, args, handler):
        if len(args) < 2:
            return self.printHelp("privacy")
        
        actionsDict = PeerActions.get().getAllPeerActions()
        
        pluginName = self.__getPluginName(args[0])
        if pluginName is None:
            print "Unknown plugin or plugin has no peer actions. Use privacy list to get a list of available peer actions."
            return
        pluginActions = actionsDict[pluginName]

        actionNameLower = args[1].lower()
        action = None
        for anAction in pluginActions:
            if actionNameLower == anAction.getName().lower():
                action = anAction
                break
        if action is None:
            print "Unknown peer action. Use privacy list to get a list of available peer actions."
            return
            
        handler(action, args[2:])
    
    def getInfo(self, action, args):
        category = None
        if not action.usesPrivacyCategories() or action.getPrivacyPolicy(categoryPolicy=PrivacySettings.CATEGORY_NEVER) != PrivacySettings.POLICY_BY_CATEGORY:
            if len(args) > 0:
                print "Action has no categories or doesn't use them. Displaying default settings."
        else:
            if len(args) > 0:
                category = args[0]
            else:
                self.__printExceptions(action, None, PrivacySettings.POLICY_PEER_EXCEPTION)
                print "Specify a category to get the category's privacy settings."
                return
        
        policy = action.getPrivacyPolicy(category)
        print "Policy:", self.__getPrivacyPolicyDescription(policy)
        if policy in (PrivacySettings.POLICY_PEER_EXCEPTION,
                      PrivacySettings.POLICY_EVERYBODY_EX,
                      PrivacySettings.POLICY_NOBODY_EX):
            self.__printExceptions(action, category, policy)
    
    def setPolicy(self, action, args):
        if len(args) == 0:
            print "No policy specified."
        if len(args) == 1:
            # change action's policy
            policy = self.__getPolicyFromText(args[0])
            if policy is None:
                print "Invalid policy:", args[0]
            else:
                if policy == PrivacySettings.POLICY_BY_CATEGORY and not action.usesPrivacyCategories():
                    print "Action has no categories. Please use another policy."
                    return
                PrivacySettings.get().setPolicy(action, None, policy, categoryPolicy=PrivacySettings.CATEGORY_NEVER)
        else:
            if not action.usesPrivacyCategories():
                print "Action has no categories."
            elif action.getPrivacyPolicy(categoryPolicy=PrivacySettings.CATEGORY_NEVER) != PrivacySettings.POLICY_BY_CATEGORY:
                print "Action's policy does not use categories. Change the action's policy to 'by category' first."
            else:
                category = args[0]
                policy = self.__getPolicyFromText(args[1])
                if policy is None:
                    print "Invalid policy:", args[1]
                else:
                    PrivacySettings.get().setPolicy(action, category, policy, categoryPolicy=PrivacySettings.CATEGORY_ALWAYS)
    
    def setState(self, action, args):
        if len(args) < 2:
            self.printHelp(u"privacy")
            return
        
        policy = action.getPrivacyPolicy(categoryPolicy=PrivacySettings.CATEGORY_NEVER)
        if policy not in (PrivacySettings.POLICY_BY_CATEGORY,
                          PrivacySettings.POLICY_EVERYBODY_EX,
                          PrivacySettings.POLICY_NOBODY_EX):
            print "The current policy does not support individual peer settings."
            return
        
        if len(args) == 2:
            category = None
            categoryPolicy = PrivacySettings.CATEGORY_NEVER
            if policy == PrivacySettings.POLICY_BY_CATEGORY:
                policy = PrivacySettings.POLICY_PEER_EXCEPTION
        else:
            if policy != PrivacySettings.POLICY_BY_CATEGORY:
                print "Action's policy does not use categories. Change the action's policy to 'by category' first."
                return
            category = args.pop(0)
            categoryPolicy = PrivacySettings.CATEGORY_ALWAYS
            
        peerIDs = self.__getPeerIDs(args[0])
        if len(peerIDs) == 0:
            print "Unknown peer:", args[0]
            return
        
        state = self.__getState(args[1], policy)
        if state is None:
            print "Invalid state:", args[1]
        
        for peerID in peerIDs:
            PrivacySettings.get().addException(action, category, policy, peerID, state, categoryPolicy=categoryPolicy)
    
    def testState(self, action, args):
        if len(args) < 1:
            self.printHelp(u"privacy")
            return
        
        if len(args) == 1:
            category = None
        else:
            category = args.pop(0)
            
        peerIDs = self.__getPeerIDs(args[0])
        if len(peerIDs) == 0:
            print "Unknown peer:", args[0]
            return
        
        self.appendOutput(u"Peer", u"State")
        self.appendSeparator()
        for peerID in peerIDs:
            state = PrivacySettings.get().getPeerState(peerID, action, category)
            peerName = get_peers().getDisplayedPeerName(pID=peerID)
            if peerName is None:
                peerName = peerID
            self.appendOutput(peerName, self.__getStateDescription(state))
        self.flushOutput()
    
    @loggingFunc
    def do_privacy(self, args):
        """
        Show or edit privacy settings.
        Usage: privacy list
                   get a list of available privacy modules
               privacy info <plugin> <action> [<category>]
                   show the settings of an action. If the action has categories,
                   specify the category to show the specific settings.
               privacy setpolicy <plugin> <action> [<category>] <policy>
                   Set the privacy policy for an action or an action's category. 
               privacy set <plugin> <action> [<category>] <peer> allow|deny|default
                   Set a peer's privacy state for an action or a action's category.
               privacy test <plugin> <action> [<category>] <peer>
                   Test what happens if a peer performs an action on you.
        """
        if len(args) == 0:
            return self.printHelp("privacy")
        args = self.getArguments(args)
        subcmd = args.pop(0)
        if subcmd == "list":
            self.listActions(args)
        elif subcmd == "info":
            self.handleSetting(args, self.getInfo)
        elif subcmd == "setpolicy":
            self.handleSetting(args, self.setPolicy)
        elif subcmd == "set":
            self.handleSetting(args, self.setState)
        elif subcmd == "test":
            self.handleSetting(args, self.testState)
        else:
            return self.printHelp("privacy")
       
    def _completePluginName(self, text):
        actionsDict = PeerActions.get().getAllPeerActions()
        for pluginName, actions in actionsDict.iteritems():
            pluginName = pluginName.replace(" ", "\\ ")
            if pluginName.lower().startswith(text):
                yield pluginName
            pluginObject = actions[0].getPluginObject()
            if pluginObject is not None:
                dispName = pluginObject.get_displayed_name().replace(" ", "\\ ")
                if dispName.lower().startswith(text):
                    yield dispName
       
    def __completeActionName(self, pluginName, text):
        actionsDict = PeerActions.get().getAllPeerActions()
        actions = actionsDict[pluginName]
        for action in actions:
            actionName = action.getName().replace(" ", "\\ ")
            if actionName.lower().startswith(text):
                yield actionName
       
    def _handleComplete(self, args, argNum, text):
        text = text.lower()
        if argNum == 0:
            # plugin name
            return self._completePluginName(text)
        elif argNum == 1:
            # action name
            pluginName = self.__getPluginName(args[0])
            if pluginName is None:
                return []
            else:
                return self.__completeActionName(pluginName, text)
       
    def __completeList(self, _args, _argNum, _text):
        return []
       
    def complete_privacy(self, text, line, begidx, endidx):
        try:
            return self.completeSubcommands(text, line, begidx, endidx, {"list": self.__completeList,
                                                                         "info": self._handleComplete,
                                                                         "setpolicy": self._handleComplete,
                                                                         "set": self._handleComplete,
                                                                         "test": self._handleComplete})
        except:
            self.logger.exception("Error completing privacy command")
    