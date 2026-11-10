'use strict';
// The part of the mongoskin 1.4 API that livedb-mongo 0.4 calls, on top of a driver that works on
// current Node. mongodb 3.7 is the last line that still speaks to the mongo:3.4 server of this
// environment (4.x needs 3.6). With ssl=true the server's certificate and host name are verified
// against MONGO_TLS_CA_FILE; there is no setting that turns the check off.
const fs = require('fs');
const { MongoClient } = require('mongodb');

const RETRY_MS = 2000;
// How long a waiting operation may wait for mongo before its callback gets the error.
const WAIT_MS = 30000;

function connect(state, url, options, caFile) {
  // Read for every attempt: the certificate may not exist yet while the mongo container is starting.
  new Promise(function (resolve) {
    const attempt = caFile ? Object.assign({}, options, { sslCA: [fs.readFileSync(caFile)] }) : options;
    resolve(new MongoClient(url, attempt).connect());
  }).then(function (client) {
    if (state.closed) {
      client.close();
      return;
    }
    state.client = client;
    state.waiters.splice(0).forEach(function (waiter) { waiter.ok(client); });
  }, function (err) {
    state.lastError = err;
    console.error('mongo connection failed, retrying: %s', err.message);
    if (!state.closed) setTimeout(function () { connect(state, url, options, caFile); }, RETRY_MS);
  });
}

function connected(state) {
  if (state.client) return Promise.resolve(state.client);
  if (state.closed) return Promise.reject(new Error('mongo connection closed'));
  return new Promise(function (resolve, reject) {
    const waiter = { ok: function (client) { clearTimeout(timer); resolve(client); } };
    const timer = setTimeout(function () {
      state.waiters.splice(state.waiters.indexOf(waiter), 1);
      reject(state.lastError || new Error('mongo is not connected'));
    }, WAIT_MS);
    state.waiters.push(waiter);
  });
}

class Collection {
  constructor(state, name) {
    this.state = state;
    this.name = name;
  }

  with(fn, callback) {
    connected(this.state).then(function (client) {
      return fn(client.db().collection(this.name));
    }.bind(this)).then(function (result) {
      if (callback) callback(null, result);
    }, function (err) {
      if (callback) callback(err);
    });
  }

  findOne(query, spec, callback) {
    if (typeof spec === 'function') { callback = spec; spec = null; }
    // livedb-mongo passes either {sort: ...} or a bare projection in the second argument.
    const options = spec && spec.sort ? spec : { projection: spec || undefined };
    this.with(function (col) { return col.findOne(query, options); }, callback);
  }

  find(query, spec, callback) {
    const options = spec && spec.sort ? spec : { projection: spec || undefined };
    const run = this.with.bind(this);
    if (callback) {
      run(function (col) { return col.find(query, options); }, callback);
      return undefined;
    }
    return { toArray: function (cb) { run(function (col) { return col.find(query, options).toArray(); }, cb); } };
  }

  update(selector, doc, options, callback) {
    this.with(function (col) { return col.replaceOne(selector, doc, options); }, callback);
  }

  save(doc, callback) {
    this.with(function (col) { return col.replaceOne({ _id: doc._id }, doc, { upsert: true }); }, callback);
  }

  ensureIndex(spec, unique, callback) {
    this.with(function (col) { return col.createIndex(spec, { unique: !!unique }); }, callback);
  }

  count(query, callback) {
    this.with(function (col) { return col.countDocuments(query); }, callback);
  }

  distinct(field, query, callback) {
    this.with(function (col) { return col.distinct(field, query); }, callback);
  }

  aggregate(pipeline, callback) {
    this.with(function (col) { return col.aggregate(pipeline).toArray(); }, callback);
  }

  mapReduce(map, reduce, options, callback) {
    this.with(function (col) { return col.mapReduce(map, reduce, options); }, callback);
  }
}

exports.db = function (url) {
  const options = { useUnifiedTopology: true };
  let caFile = null;
  if (/[?&](ssl|tls)=true/.test(url)) {
    if (!process.env.MONGO_TLS_CA_FILE) throw new Error('MONGO_TLS_CA_FILE is required for a TLS connection to mongo');
    options.sslValidate = true;  // off by default in this driver line, and tlsCAFile alone does not turn it on
    options.checkServerIdentity = true;
    caFile = process.env.MONGO_TLS_CA_FILE;
  }
  const state = { client: null, closed: false, waiters: [], lastError: null };
  connect(state, url, options, caFile);
  return {
    collection: function (name) { return new Collection(state, name); },
    close: function (callback) {
      state.closed = true;
      const client = state.client;
      if (!client) {
        callback(null);
        return;
      }
      client.close().then(function () { callback(null); }, callback);
    },
  };
};
