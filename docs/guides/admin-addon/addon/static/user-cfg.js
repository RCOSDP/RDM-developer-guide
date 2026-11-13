'use strict';

require('js/osfToggleHeight');
var osfHelpers = require('js/osfHelpers');

var SHORT_NAME = 'myskelton';
var FULL_NAME = 'My Skelton';

function UserSettings() {
    var self = this;
    self.properName = FULL_NAME;
}

var settings = new UserSettings();
osfHelpers.applyBindings(settings, '#' + SHORT_NAME + 'AddonScope');
