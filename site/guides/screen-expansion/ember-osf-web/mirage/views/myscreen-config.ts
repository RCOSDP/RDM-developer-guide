import { HandlerContext, Schema } from 'ember-cli-mirage';

export function myscreenConfig(this: HandlerContext, schema: Schema) {
    const model = schema.myscreenConfigs.first();
    const json = this.serialize(model);
    return json;
}
