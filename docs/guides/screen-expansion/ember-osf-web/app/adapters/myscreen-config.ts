import DS from 'ember-data';
import config from 'ember-get-config';
import OsfAdapter from './osf-adapter';

const {
    OSF: {
        url: host,
        webApiNamespace: namespace,
    },
} = config;

export default class MyScreenConfigAdapter extends OsfAdapter {
    host = host.replace(/\/+$/, '');
    namespace = namespace;

    buildURL(
        _: string | undefined,
        id: string | null,
        __: DS.Snapshot | null,
        ___: string,
        ____?: {},
    ): string {
        const nodeUrl = super.buildURL('node', null, null, 'findRecord', {});
        const url = nodeUrl.replace(/\/nodes\/$/, '/project/');
        return `${url}${id}/myscreen/config`;
    }
}

declare module 'ember-data/types/registries/adapter' {
    export default interface AdapterRegistry {
        'myscreen-config': MyScreenConfigAdapter;
    } // eslint-disable-line semi
}
