from shapely.geometry import Point, Polygon

def test_boundary_distance_zero_inside():
    parcel=Polygon([(0,0),(1,0),(1,1),(0,1)])
    facility=Point(.5,.5)
    assert parcel.distance(facility)==0

def test_boundary_distance_positive_outside():
    parcel=Polygon([(0,0),(1,0),(1,1),(0,1)])
    facility=Point(2,2)
    assert parcel.distance(facility)>0
