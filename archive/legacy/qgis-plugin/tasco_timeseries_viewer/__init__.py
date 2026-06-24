def classFactory(iface):
    from .plugin import TascoTimeseriesViewer
    return TascoTimeseriesViewer(iface)
