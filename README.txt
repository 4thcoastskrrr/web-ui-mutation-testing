(1)dataフォルダ内にテスト対象のアプリケーションのためのフォルダを作る
例　data/syuugaku

(2)(1)のフォルダ内にテストシナリオごとのフォルダを作る
例　data/syuugaku/scenario1

(3)(2)のscenarioフォルダ内にSelenium IDEを使って生成されたテストスクリプト(名前はtest_org.py)をoriginalフォルダを作ってその中に置く
例　data/syuugaku/scenario1/original/test_org.py

(4)(3)で用意したテストスクリプトを元に変異版のテストスクリプトを自動生成する
例
テストコード変換
python tool/generate_pageobject.py data/syuugaku/scenario1 

python tool/generate_locators.py data/syuugaku/scenario1 

(ここでmutationフォルダを作成している)


ミューテーション生成
python tool/mutation_sentence_erase.py data/syuugaku/scenario1

python tool/mutation_code_rotation.py data/syuugaku/scenario1

python tool/mutation_locators_rotation.py data/syuugaku/scenario1

python tool/mutation_string_edit.py data/syuugaku/scenario1 --max-symbol 5 --max-delete 3 --max-swap 5



(5)(4)で生成したテストスクリプトをすべて自動実行する
（ミューテーションを全て実行してから元のnewフォルダのプログラムにも差分とスクリーンショットが取れるようにコードを追加して実行する）
python tool/run_tests.py data/syuugaku/scenario1 

(6)HTMLを比較して構造差分を計算する・各ファイル と距離のデータをreport.csvに保存
python tool/html_editdistance.py data/syuugaku1/scenario1/new data/syuugaku1/scenario1/mutants 
--strip-scripts --mask-formkey --mask-random-id --zero-timestamp --exclude '#minicart,.modal-popup,.modal-overlay,.captcha,script[type="application/json"],#btn-minicart,.message,.loading-mask'    

(7)構造差分がないものに対してスクリーンショットを用いて内容差分比較・差分の有無でグルーピング
python tool/diff_screenshot.py  data/test/scenario3/new data/test/scenario3/mutation



