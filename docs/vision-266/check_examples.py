"""[designed: #266/R1] Negative controls for static authoring claims only.

Run after render.py --check. Mutations stay in memory/temporary directories;
retained source and images are never rewritten. No game behavior is exercised.
"""
import copy
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import render as r

NS={'s':'http://www.w3.org/2000/svg'}


def rejects(label, action):
    try:
        action()
    except AssertionError:
        print('REJECT '+label)
    else:
        raise AssertionError('Mutation falsely accepted: '+label)


def svg_case(label, number, selector, change):
    source=next((r.ROOT/'screens').glob(f'{number:02}-*.svg')).read_text()
    root=ET.fromstring(source)
    element=root.find(selector,NS)
    assert element is not None, (label,selector)
    change(element)
    rejects(label,lambda:r.check_svg(ET.tostring(root,encoding='unicode'),number))
    r.check_svg(source,number)


def main():
    bar='.//s:g[@data-attribute="Crossing"]'
    segment=bar+'/s:rect'
    svg_case('SVG missing segments',4,bar,lambda el:[el.remove(c) for c in list(el) if c.tag.endswith('rect')])
    svg_case('SVG descriptor removed',4,'.//s:g[@data-descriptor="Energy"]',lambda el:el.clear())
    svg_case('SVG printed raw value',4,bar+'/s:g[@data-raw="value"]/s:text',lambda el:setattr(el,'text','2'))
    svg_case('SVG zero segment height',4,segment,lambda el:el.set('height','0'))
    svg_case('SVG zero segment width',4,segment,lambda el:el.set('width','0'))
    svg_case('SVG filled count forged',4,bar,lambda el:el.set('data-filled','1'))
    svg_case('SVG characteristic formula forged',4,'.//s:g[@data-attribute="Energy"]',lambda el:el.set('data-filled','1'))
    svg_case('SVG actual field shrunk',6,'.//s:rect[@data-kind="playing-field"]',lambda el:el.set('width','140'))
    svg_case('SVG black roster name',3,'.//s:g[@data-roster="NL01"]/s:text[2]',lambda el:el.set('fill',r.BLACK))
    svg_case('SVG bar text too small',4,bar+'/s:text',lambda el:el.set('font-size','8'))
    svg_case('SVG third recent line',6,'.//s:g[@data-commentary="recent"]',lambda el:el.append(copy.deepcopy(el[0])))
    svg_case('SVG focus chrome injected',14,'.',lambda el:ET.SubElement(el,'{'+NS['s']+'}g',{'data-chrome':'side'}))

    # Fresh scratch modules exercise the four source-level bypasses in R1;
    # the checker is unchanged and cannot inherit the author's stored metadata.
    source=Path(r.__file__).read_text()
    cases=[
        ('source invisible segments','max(1,step-2),size-3,WHITE','max(1,step-2),0,WHITE'),
        ('source inverted skill bars','half,25,val,name,val','half,25,25-val,name,val'),
        ('source field shrunk with surround retained','w-18,h-18,BLACK,GREY,kind=','w*.3,h*.3,BLACK,GREY,kind='),
        ('source black roster names',"selected_color=BLACK if k==selected else ROLE_COLORS[P[k]['role']]",'selected_color=BLACK')]
    for label,before,after in cases:
        assert source.count(before)==1, label
        namespace={'__file__':r.__file__,'__name__':'scratch_negative_control'}
        exec(compile(source.replace(before,after),r.__file__,'exec'),namespace)
        with tempfile.TemporaryDirectory(prefix='goal2-266-negative-') as directory:
            rejects(label,lambda:namespace['draw'](Path(directory)))

    saved=copy.deepcopy(r.D)
    cases=[
        ('duplicate squad',lambda:r.D['initial_squad'].__setitem__(1,'NL01')),
        ('wrong half-time score',lambda:r.D.__setitem__('halftime_score',[0,0])),
        ('bench scorer',lambda:r.D['events'][0].__setitem__('player','NL14')),
        ('wrong scorer minute',lambda:r.D['events'][0].__setitem__('minute',19)),
        ('five defenders in 4-4-2',lambda:r.P['NL06'].__setitem__('role','CB')),
        ('cloned profile',lambda:r.P['NL14'].__setitem__('skills',r.P['NL08']['skills'][:])),
        ('out-of-domain characteristic',lambda:r.P['NL14'].__setitem__('leadership',8))]
    try:
        for label,change in cases:
            change()
            rejects(label,r.validate_scenario)
            r.D.clear();r.D.update(copy.deepcopy(saved));r.P={p['key']:p for p in r.D['players']}
            r.validate_scenario()
    finally:
        r.D.clear();r.D.update(saved);r.P={p['key']:p for p in r.D['players']}
    r.validate_scenario()
    print('PASS 12 SVG, 4 source and 7 scenario negative controls; retained files untouched')


if __name__=='__main__':main()
