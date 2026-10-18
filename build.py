# 使い方: python3 build.py
#   index.src.html → index.html（BudouX処理）を生成したうえで、
#   dist/solo（男性仲人1名）と dist/duo（2名体制）の2セットを書き出します。
import re, shutil, subprocess, pathlib
root=pathlib.Path(__file__).parent
subprocess.run(['python3',str(root/'budoux_apply.py')],check=True)
html=(root/'index.html').read_text(encoding='utf-8')
legal={f:(root/f).read_text(encoding='utf-8') for f in ['company.html','tokushoho.html','privacy.html','policy.html']}
variants={
 'solo':{'rep':'鶴田 幸奈（代表仲人）','to':'中野 裕亮（代表仲人）','rep2':'<td>鶴田 幸奈</td>','to2':'<td>中野 裕亮</td>',
         'staff':'鶴田 幸奈（IBJ認定婚活カウンセラー）／ 中野 裕亮（IBJ認定婚活カウンセラー）','staff_to':'中野 裕亮（IBJ認定婚活カウンセラー）'},
 'duo':{}
}
for name,v in variants.items():
    out=root/'dist'/name
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(root/'images',out/'images')
    h=re.sub(r'(<body[^>]*?)data-team="(solo|duo)"',lambda m:m.group(1)+f'data-team="{name}"',html,count=1)
    (out/'index.html').write_text(h,encoding='utf-8')
    for f,t in legal.items():
        if v:
            t=t.replace(v['rep'],v['to']).replace(v['rep2'],v['to2']).replace(v['staff'],v['staff_to'])
        (out/f).write_text(t,encoding='utf-8')
    print('built',out)
