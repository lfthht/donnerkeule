"""Temporary stock amdgpu DPM states, with exact device and auto-mode recovery."""
from pathlib import Path
import re


def inspect(root=Path('/sys/class/drm')):
    result = {}
    for card in root.glob('card[0-9]*'):
        device = (card/'device').resolve()
        mode = device/'power_dpm_force_performance_level'
        if not mode.is_file() or (device/'vendor').read_text().strip() != '0x1002':
            continue
        result[str(device)] = {
            'vendor': (device/'vendor').read_text().strip(),
            'device': (device/'device').read_text().strip(),
            'mode': mode.read_text().strip(),
            'clocks': {name: (device/name).read_text() for name in
                       ('pp_dpm_fclk', 'pp_dpm_socclk', 'pp_dpm_mclk') if (device/name).is_file()},
        }
    if not result:
        raise RuntimeError('No AMD GPU power interface found')
    return result


def snapshot(root=Path('/sys/class/drm')):
    result = inspect(root)
    if any(v['mode'] != 'auto' for v in result.values()):
        raise RuntimeError('Power experiment requires an auto-mode baseline')
    return result


def validate(before, current):
    if set(before) != set(current) or any(
            before[p][k] != current[p][k] for p in before for k in ('vendor', 'device')):
        raise RuntimeError('AMD GPU identities differ from recovery snapshot')
    if any(v['mode'] != 'auto' for v in before.values()):
        raise RuntimeError('Recovery snapshot does not contain auto mode')


def restore(before, root=Path('/sys/class/drm')):
    validate(before, inspect(root))
    errors = []
    for device, item in before.items():
        try:
            path = Path(device)/'power_dpm_force_performance_level'
            path.write_text(item['mode']+'\n')
            if path.read_text().strip() != item['mode']:
                raise RuntimeError('GPU power-mode recovery readback differs')
        except Exception as error:
            errors.append(str(error))
    if errors:
        raise RuntimeError('; '.join(errors))
    return inspect(root)


def apply(before, mode, fclk=None, socclk=None, root=Path('/sys/class/drm')):
    current = inspect(root)
    validate(before, current)
    if mode not in ('auto', 'high', 'profile_peak', 'manual'):
        raise ValueError('Unsupported temporary power mode')
    indices = {'pp_dpm_fclk': fclk, 'pp_dpm_socclk': socclk}
    if any(x is not None for x in indices.values()) and mode != 'manual':
        raise ValueError('Stock clock indices require manual mode')
    # Validate every requested stock index on every GPU before the first write.
    for item in current.values():
        for name, index in indices.items():
            if index is None:
                continue
            available = {int(x) for x in re.findall(r'^\s*(\d+):', item['clocks'].get(name, ''), re.M)}
            if type(index) is not int or index not in available:
                raise ValueError('Clock index not in the GPU stock table: '+name)
    try:
        for device in before:
            path = Path(device)/'power_dpm_force_performance_level'
            # Reset any preceding trial's constraints before applying this one.
            path.write_text('auto\n')
            path.write_text(mode+'\n')
            if path.read_text().strip() != mode:
                raise RuntimeError('Temporary GPU power-mode readback differs')
            for name, index in indices.items():
                if index is not None:
                    (Path(device)/name).write_text(str(index)+'\n')
        return inspect(root)
    except Exception:
        restore(before, root)
        raise
