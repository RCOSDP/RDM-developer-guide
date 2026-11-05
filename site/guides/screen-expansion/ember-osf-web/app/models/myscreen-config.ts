import DS from 'ember-data';
import OsfModel from './osf-model';

const { attr } = DS;

export default class MyScreenConfigModel extends OsfModel {
    @attr('string') param1!: string;
}

declare module 'ember-data/types/registries/model' {
    export default interface ModelRegistry {
        'myscreen-config': MyScreenConfigModel;
    } // eslint-disable-line semi
}
