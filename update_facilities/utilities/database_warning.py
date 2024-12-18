from qgis.utils import iface


def database_warning(warn_title: str, warn_message: str, warn_level: str):
    """
    push message to messageBar

    @param warn_text:           warning type
    @type warn_text:            string
    @param warn_message         message to display to user
    @type warn_message          string
    @param warn_level_text      level of warning
    @type warn_level_text       string
    """
    if warn_level == "info":
        iface.messageBar().pushInfo(warn_title, warn_message)
    elif warn_level == "warning":
        iface.messageBar().pushWarning(warn_title, warn_message)
    elif warn_level == "critical":
        iface.messageBar().pushCritical(warn_title, warn_message)
