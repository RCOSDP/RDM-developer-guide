'use strict';

var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');
var OAuthAddonSettingsViewModel = require('../rdmAddonSettings.js').OAuthAddonSettingsViewModel;
var oop = require('js/oop');

var _ = require('js/rdmGettext')._;

var ViewModel = oop.extend(OAuthAddonSettingsViewModel, {
  constructor: function(url, institutionId) {
    this.super.constructor.call(this, 'myskelton', 'My Skelton', institutionId);

    this.adminNotes = ko.observable('');
    this.isSavingAdminNotes = ko.observable(false);
  },

  saveAdminNotes: function() {
    var self = this;
    self.isSavingAdminNotes(true);
    var adminNotes = self.adminNotes().trim();

    var url = '/addons/api/v1/settings/' + this.name + '/' + this.institutionId + '/adminnotes/';
    return $.ajax({
      url: url,
      type: 'PUT',
      data: JSON.stringify({admin_notes: adminNotes}),
      contentType: 'application/json',
      dataType: 'json'
    }).then(function() {
      return self.fetchAdminNotes();
    }).done(function() {
      self.setMessage(_('Saving admin notes was successful'), 'text-success');
    }).fail(function(xhr, status, error) {
      Raven.captureMessage(_('Error while saving admin notes'), {
        extra: {
          url: url,
          status: status,
          error: error
        }
      });
      if (error === 'Unauthorized' || error === 'Forbidden') {
        self.setMessage(_('Permission error while saving admin notes'), 'text-danger');
      } else {
        self.setMessage(_('Error while saving admin notes'), 'text-danger');
      }
    }).always(function() {
      self.isSavingAdminNotes(false);
    });
  },

  fetchAdminNotes: function(){
    var self = this;
    var url = '/addons/api/v1/settings/' + self.name + '/' + self.institutionId + '/adminnotes/';
    return $.ajax({
      url: url,
      type: 'GET',
      dataType: 'json'
    }).done(function(data) {
      self.adminNotes(data.admin_notes);
    }).fail(function(xhr, status, error) {
      Raven.captureMessage(_('Error while fetching admin notes'), {
        extra: {
          url: url,
          status: status,
          error: error
        }
      });
    });
  },
});

function MySkeltonUserConfig(selector, url, institutionId) {
  var viewModel = new ViewModel(url, institutionId);
  ko.applyBindings(viewModel, $(selector)[0]);
  viewModel.fetchAdminNotes()
    .fail(function() {
      viewModel.setMessage(_('Error while fetching admin notes'), 'text-danger');
    });
}

module.exports = {
  MySkeltonViewModel: ViewModel,
  MySkeltonUserConfig: MySkeltonUserConfig
};
