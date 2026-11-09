'use strict';
// The part of the mongoskin 1.4 API that livedb-mongo 0.4 calls, on top of a driver that works on
// current Node. mongodb 3.7 is the last line that still speaks to the mongo:3.4 server of this
// environment (4.x needs 3.6). The certificate check is off for ssl=true, as it was in mongodb 1.4,
// because the server uses a self-signed certificate made at container start.
const { MongoClient } = require('mongodb');

const RETRY_MS = 2000;

function connect(url, options) {
  return new MongoClient(url, options).connect().catch(function (err) {
    console.error('mongo connection failed, retrying: %s', err.message);
    return new Promise(function (resolve) {
      setTimeout(function () { resolve(connect(url, options)); }, RETRY_MS);
    });
  });
}

class Collection {
  constructor(client, name) {
    this.client = client;
    this.name = name;
  }

  with(fn, callback) {
    this.client.then(function (client) {
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
  if (/[?&](ssl|tls)=true/.test(url)) options.tlsAllowInvalidCertificates = true;
  const client = connect(url, options);
  return {
    collection: function (name) { return new Collection(client, name); },
    close: function (callback) {
      client.then(function (c) { return c.close(); }).then(function () { callback(null); }, callback);
    },
  };
};
