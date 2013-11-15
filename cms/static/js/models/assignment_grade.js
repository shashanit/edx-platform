define(["backbone", "underscore"], function(Backbone, _) {
    var AssignmentGrade = Backbone.Model.extend({
        defaults : {
            graderType : null, // the type label (string). May be "Not Graded" which implies None. 
            location : null // A location object
        },
        initialize : function(attrs) {
            if (attrs['assignmentUrl']) {
                this.set('location', new Location(attrs['assignmentUrl'], {parse: true}));
            }
        },
        urlRoot : function() {
            // return locator.url_reverse('xblock', 'gradeas') + '/' + graderType
            if (this.has('location')) {
                var location = this.get('location');
                return '/' + location.get('org') + "/" + location.get('course') + '/' + location.get('category') + '/'
                + location.get('name') + '/gradeas/';
            }
            else return "";
        }
    });
    return AssignmentGrade;
});
