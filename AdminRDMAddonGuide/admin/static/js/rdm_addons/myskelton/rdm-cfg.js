'use strict';
var $ = require('jquery');
var MySkeltonUserConfig = require('./myskeltonRdmConfig.js').MySkeltonUserConfig;

var institutionId = $('#myskeltonAddonScope').data('institution-id');
var url = '/addons/api/v1/settings/myskelton/' + institutionId + '/accounts/';
var myskeltonUserConfig = new MySkeltonUserConfig('#myskeltonAddonScope', url, institutionId);