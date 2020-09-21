<div id="${addon_short_name}Scope" class="scripted">
    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url}>
        ${addon_full_name}
    </h4>
    <!-- Settings Pane -->
    <div class="${addon_short_name}-settings">
        <div class="row">
            <div class="col-md-12">
                <div class="pull-right">
                    <button class="btn btn-success" data-bind="enable: dirty, click: submit">
                        ${_("Save")}
                    </button>
                </div>
            </div>
            <!-- end col -->
        </div>
        <!-- end row -->
        <div class="row">
            <div class="col-md-12">
                <input class="form-control" data-bind="textInput: param_1" id="param_1" name="param_1" />
            </div>
            <!-- end col -->
        </div>
        <!-- end row -->
    </div>
</div>
