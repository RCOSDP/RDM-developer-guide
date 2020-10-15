'use strict';

var MyMinIOUserConfig = require('./myminioUserConfig.js').MyMinIOUserConfig;
var url = '/api/v1/settings/myminio/accounts/';
new MyMinIOUserConfig('#myminioAddonScope', url);
