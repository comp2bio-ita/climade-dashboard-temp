window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, context) {
                const {
                    classes,
                    colorscale,
                    style,
                    colorProp
                } = context.hideout; // get props from hideout
                const value = feature.properties[colorProp] // get value the determines the color
                for (let i = 0; i < classes.length; ++i) {
                    if (value > classes[i]) {
                        style.fillColor = colorscale[i]; // set the fill color according to the class
                    }
                }
                return style;
            }

            ,
        function1: function(feature, latlng, context) {
            const extendexDivIcon = L.DivIcon.extend({
                createIcon: function(oldIcon) {
                    let icon = L.DivIcon.prototype.createIcon.call(this, oldIcon);
                    icon.style.backgroundColor = this.options.color;
                    icon.style.border = this.options.border;
                    return icon;
                }
            })

            const {
                icon_size
            } = context.hideout

            const icon_item = new extendexDivIcon({
                html: feature.properties.icon,
                iconSize: [icon_size, icon_size],
                color: "transparent",
                border: "none"
            });

            return L.marker(latlng, {
                icon: icon_item,
                riseOnHover: true,
                riseOffset: 250
            });
        }
    }
});