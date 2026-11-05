import OsfSerializer from './osf-serializer';

export default class MyScreenConfigSerializer extends OsfSerializer {
}

declare module 'ember-data/types/registries/serializer' {
    export default interface SerializerRegistry {
        'myscreen-config': MyScreenConfigSerializer;
    } // eslint-disable-line semi
}
