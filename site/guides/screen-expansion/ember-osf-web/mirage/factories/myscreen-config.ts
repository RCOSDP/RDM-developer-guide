import { Factory } from 'ember-cli-mirage';

import MyScreenConfigModel from 'ember-osf-web/models/iqbrims-status';

export default Factory.extend<MyScreenConfigModel>({
});

declare module 'ember-cli-mirage/types/registries/schema' {
    export default interface MirageSchemaRegistry {
        myscreenConfigs: MyScreenConfigModel;
    } // eslint-disable-line semi
}
