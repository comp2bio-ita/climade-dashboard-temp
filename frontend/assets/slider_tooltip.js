window.dccFunctions = window.dccFunctions || {};

// Formats the advanced-filter date RangeSlider tooltip. The slider value is absolute days since the
// Unix epoch, so multiplying by the ms-per-day gives the UTC midnight of that date.
window.dccFunctions.sliderDaysToDate = function (value) {
    return new Date(value * 86400000).toISOString().slice(0, 10);
};
