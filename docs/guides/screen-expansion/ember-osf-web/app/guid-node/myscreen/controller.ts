import Controller from '@ember/controller';
import EmberError from '@ember/error';
import { action, computed } from '@ember/object';
import { reads } from '@ember/object/computed';
import { inject as service } from '@ember/service';

import DS from 'ember-data';

import Intl from 'ember-intl/services/intl';
import MyScreenConfigModel from 'ember-osf-web/models/myscreen-config';
import Node from 'ember-osf-web/models/node';
import Analytics from 'ember-osf-web/services/analytics';
import StatusMessages from 'ember-osf-web/services/status-messages';
import Toast from 'ember-toastr/services/toast';

export default class GuidNodeMyScreen extends Controller {
    @service toast!: Toast;
    @service intl!: Intl;
    @service statusMessages!: StatusMessages;
    @service analytics!: Analytics;

    @reads('model.taskInstance.value')
    node?: Node;

    isPageDirty = false;

    configCache?: DS.PromiseObject<MyScreenConfigModel>;

    @computed('config.isFulfilled')
    get loading(): boolean {
        return !this.config || !this.config.get('isFulfilled');
    }

    @action
    save(this: GuidNodeMyScreen) {
        if (!this.config) {
            throw new EmberError('Illegal config');
        }
        const config = this.config.content as MyScreenConfigModel;

        config.save()
            .then(() => {
                this.set('isPageDirty', false);
            })
            .catch(() => {
                this.saveError(config);
            });
    }

    saveError(config: MyScreenConfigModel) {
        config.rollbackAttributes();
        const message = this.intl.t('myscreen.failed_to_save');
        this.toast.error(message);
    }

    @computed('config.param1')
    get param1() {
        if (!this.config || !this.config.get('isFulfilled')) {
            return '';
        }
        const config = this.config.content as MyScreenConfigModel;
        return config.param1;
    }

    set param1(v: string) {
        if (!this.config) {
            throw new EmberError('Illegal config');
        }
        const config = this.config.content as MyScreenConfigModel;
        config.set('param1', v);
        this.set('isPageDirty', true);
    }

    @computed('node')
    get config(): DS.PromiseObject<MyScreenConfigModel> | undefined {
        if (this.configCache) {
            return this.configCache;
        }
        if (!this.node) {
            return undefined;
        }
        this.configCache = this.store.findRecord('myscreen-config', this.node.id);
        return this.configCache!;
    }
}

declare module '@ember/controller' {
    interface Registry {
        'guid-node/myscreen': GuidNodeMyScreen;
    }
}
