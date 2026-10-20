"""Frozen modes; MHz and UART baud describe different clocks."""
RELEASE='20261020_pll_modes_v1'
MODES={300:0x0218,150:0x0418,25:0x0a18}
PLANS={
    'bypass':[('cold_bypass',25)],
    'switch':[('start300',300),('down150',150),('to_bypass',25),
              ('return300',300),('same300_apply',300)],
    'errors':[('start300',300),('busy_apply150',150)]}
ERROR_CHECKS=('illegal_uart_command','reserved_config','invalid_n','invalid_output',
              'busy_shadow_rejected','busy_apply_rejected','clear_error_while_busy',
              'apply_aborts_compute','baud_margin_minus','baud_margin_plus')


def cases(value):
    result=list(PLANS) if value=='all' else value.split(',')
    if not result or len(set(result))!=len(result) or any(c not in PLANS for c in result):
        raise ValueError('Cases: all or distinct bypass,switch,errors')
    return result


def corner(value):
    if value not in ('WC','BC'):raise ValueError('CORNER=WC|BC; no silent fallback')
    return value
