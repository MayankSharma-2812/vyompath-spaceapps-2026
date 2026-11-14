import React, { useEffect, useRef } from 'react';
import 'ol/ol.css';
import Map from 'ol/Map';
import View from 'ol/View';
import { marsProjection, MARS_EXTENT } from './marsProjection';

interface MapCanvasProps {
  className?: string;
}

export const MapCanvas: React.FC<MapCanvasProps> = ({ className = '' }) => {
  const mapElementRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!mapElementRef.current) return;

    const map = new Map({
      target: mapElementRef.current,
      layers: [],
      view: new View({
        projection: marsProjection,
        center: [0, 0],
        zoom: 1.5,
        minZoom: 1,
        maxZoom: 10,
        extent: MARS_EXTENT,
      }),
      controls: [],
    });

    return () => {
      map.setTarget(undefined);
    };
  }, []);

  return (
    <div
      ref={mapElementRef}
      className={`mars-map-canvas ${className}`}
      data-testid="mars-map-canvas"
    />
  );
};

export default MapCanvas;
