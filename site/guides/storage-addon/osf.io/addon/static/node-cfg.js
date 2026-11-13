'use strict';

var MyMinIONodeConfig = require('./myminioNodeConfig.js').MyMinIONodeConfig;
var url = window.contextVars.node.urls.api + 'myminio/settings/';
new MyMinIONodeConfig('My MinIO', '#myminioScope', url, '#myminioGrid');
