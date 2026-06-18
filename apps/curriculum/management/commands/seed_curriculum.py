from django.core.management.base import BaseCommand
from apps.curriculum.models import Subject, Chapter, Topic

class Command(BaseCommand):
    help = 'Seeds initial CA Foundation curriculum details: subjects, chapters, and topics'

    def handle(self, *args, **options):
        self.stdout.write("Deleting existing curriculum data...")
        Topic.objects.all().delete()
        Chapter.objects.all().delete()
        Subject.objects.all().delete()

        self.stdout.write("Seeding subjects...")
        
        # Define Subjects
        subjects_data = [
            {
                'name': 'Paper 1: Accounting',
                'code': 'ACC',
                'description': 'Principles and Practice of Accounting, journal entries, ledgers, final accounts, and partnership books.',
                'order': 1,
                'icon': 'BookOpen',
                'color': '#6366f1',
                'total_weightage': 100
            },
            {
                'name': 'Paper 2: Business Laws',
                'code': 'LAW',
                'description': 'Indian Regulatory Framework, Indian Contract Act, Sale of Goods Act, Indian Partnership Act, and Companies Act.',
                'order': 2,
                'icon': 'Scale',
                'color': '#f43f5e',
                'total_weightage': 100
            },
            {
                'name': 'Paper 3: Quantitative Aptitude',
                'code': 'QA',
                'description': 'Business Mathematics, Logical Reasoning, and Statistics basics.',
                'order': 3,
                'icon': 'Calculator',
                'color': '#10b981',
                'total_weightage': 100
            },
            {
                'name': 'Paper 4: Business Economics',
                'code': 'ECO',
                'description': 'Microeconomics basics, theory of demand and supply, market structures, and national income calculations.',
                'order': 4,
                'icon': 'TrendingUp',
                'color': '#a855f7',
                'total_weightage': 100
            }
        ]

        subjects = {}
        for s_info in subjects_data:
            subj = Subject.objects.create(**s_info)
            subjects[subj.code] = subj
            self.stdout.write(f"  Created Subject: {subj.name}")

        self.stdout.write("Seeding chapters and topics...")

        # 1. Accounting Chapters & Topics
        acc_chapters = [
            {
                'name': 'Theoretical Framework',
                'order': 1,
                'weightage': 10,
                'estimated_hours': 6.0,
                'topics': [
                    {'name': 'Meaning and Scope of Accounting', 'order': 1, 'importance_score': 3, 'estimated_minutes': 45},
                    {'name': 'Accounting Concepts and Principles', 'order': 2, 'importance_score': 5, 'estimated_minutes': 60},
                    {'name': 'Capital and Revenue Expenditures', 'order': 3, 'importance_score': 4, 'estimated_minutes': 45},
                    {'name': 'Contingent Assets and Liabilities', 'order': 4, 'importance_score': 2, 'estimated_minutes': 30}
                ]
            },
            {
                'name': 'Accounting Process',
                'order': 2,
                'weightage': 15,
                'estimated_hours': 10.0,
                'topics': [
                    {'name': 'Journal and Ledger Entries', 'order': 1, 'importance_score': 4, 'estimated_minutes': 60},
                    {'name': 'Cash Book and Subsidiary Books', 'order': 2, 'importance_score': 4, 'estimated_minutes': 60},
                    {'name': 'Trial Balance preparation', 'order': 3, 'importance_score': 3, 'estimated_minutes': 45},
                    {'name': 'Rectification of Errors', 'order': 4, 'importance_score': 5, 'estimated_minutes': 90}
                ]
            },
            {
                'name': 'Bank Reconciliation Statement',
                'order': 3,
                'weightage': 10,
                'estimated_hours': 5.0,
                'topics': [
                    {'name': 'Causes of difference between Passbook and Cashbook', 'order': 1, 'importance_score': 4, 'estimated_minutes': 45},
                    {'name': 'Preparation of BRS with Adjusted Cash Book', 'order': 2, 'importance_score': 5, 'estimated_minutes': 60}
                ]
            },
            {
                'name': 'Valuation of Inventories',
                'order': 4,
                'weightage': 8,
                'estimated_hours': 4.0,
                'topics': [
                    {'name': 'Cost of Inventory determination', 'order': 1, 'importance_score': 3, 'estimated_minutes': 45},
                    {'name': 'Inventory Valuation methods (FIFO, LIFO, WACC)', 'order': 2, 'importance_score': 5, 'estimated_minutes': 60}
                ]
            }
        ]

        # 2. Law Chapters & Topics
        law_chapters = [
            {
                'name': 'Indian Regulatory Framework',
                'order': 1,
                'weightage': 5,
                'estimated_hours': 3.0,
                'topics': [
                    {'name': 'Introduction to Legal System in India', 'order': 1, 'importance_score': 2, 'estimated_minutes': 30},
                    {'name': 'Sources of Law and Legislative Procedure', 'order': 2, 'importance_score': 3, 'estimated_minutes': 45}
                ]
            },
            {
                'name': 'The Indian Contract Act, 1872',
                'order': 2,
                'weightage': 25,
                'estimated_hours': 18.0,
                'topics': [
                    {'name': 'Essentials of a Valid Contract', 'order': 1, 'importance_score': 5, 'estimated_minutes': 90},
                    {'name': 'Offer and Acceptance rules', 'order': 2, 'importance_score': 5, 'estimated_minutes': 60},
                    {'name': 'Capacity of Parties and Consideration', 'order': 3, 'importance_score': 4, 'estimated_minutes': 75},
                    {'name': 'Free Consent constraints (Coercion, Fraud)', 'order': 4, 'importance_score': 5, 'estimated_minutes': 90},
                    {'name': 'Breach of Contract and Remedies', 'order': 5, 'importance_score': 5, 'estimated_minutes': 60}
                ]
            },
            {
                'name': 'The Sale of Goods Act, 1930',
                'order': 3,
                'weightage': 15,
                'estimated_hours': 10.0,
                'topics': [
                    {'name': 'Formation of Contract of Sale', 'order': 1, 'importance_score': 3, 'estimated_minutes': 45},
                    {'name': 'Conditions and Warranties distinctions', 'order': 2, 'importance_score': 5, 'estimated_minutes': 60},
                    {'name': 'Transfer of Ownership & Delivery', 'order': 3, 'importance_score': 4, 'estimated_minutes': 60},
                    {'name': 'Rights of an Unpaid Seller', 'order': 4, 'importance_score': 5, 'estimated_minutes': 75}
                ]
            }
        ]

        # 3. Quantitative Aptitude Chapters & Topics
        qa_chapters = [
            {
                'name': 'Ratio, Proportion, Indices and Logarithms',
                'order': 1,
                'weightage': 8,
                'estimated_hours': 5.0,
                'topics': [
                    {'name': 'Ratio and Proportion formulas', 'order': 1, 'importance_score': 3, 'estimated_minutes': 45},
                    {'name': 'Laws of Indices and Exponential rules', 'order': 2, 'importance_score': 3, 'estimated_minutes': 45},
                    {'name': 'Properties of Logarithms', 'order': 3, 'importance_score': 4, 'estimated_minutes': 60}
                ]
            },
            {
                'name': 'Equations and Matrices',
                'order': 2,
                'weightage': 12,
                'estimated_hours': 8.0,
                'topics': [
                    {'name': 'Linear and Quadratic Equations', 'order': 1, 'importance_score': 4, 'estimated_minutes': 60},
                    {'name': 'Simultaneous Linear Equations', 'order': 2, 'importance_score': 4, 'estimated_minutes': 60},
                    {'name': 'Matrix Algebra and Cramers Rule', 'order': 3, 'importance_score': 4, 'estimated_minutes': 90}
                ]
            },
            {
                'name': 'Linear Inequalities',
                'order': 3,
                'weightage': 5,
                'estimated_hours': 3.0,
                'topics': [
                    {'name': 'Linear Inequalities formulation and graphs', 'order': 1, 'importance_score': 3, 'estimated_minutes': 45}
                ]
            }
        ]

        # 4. Economics Chapters & Topics
        eco_chapters = [
            {
                'name': 'Introduction to Business Economics',
                'order': 1,
                'weightage': 10,
                'estimated_hours': 4.0,
                'topics': [
                    {'name': 'Nature and Scope of Business Economics', 'order': 1, 'importance_score': 3, 'estimated_minutes': 45},
                    {'name': 'Central Problems of an Economy', 'order': 2, 'importance_score': 4, 'estimated_minutes': 60}
                ]
            },
            {
                'name': 'Theory of Demand and Supply',
                'order': 2,
                'weightage': 20,
                'estimated_hours': 12.0,
                'topics': [
                    {'name': 'Law of Demand and Consumer Equilibrium', 'order': 1, 'importance_score': 5, 'estimated_minutes': 75},
                    {'name': 'Elasticity of Demand (Price, Income, Cross)', 'order': 2, 'importance_score': 5, 'estimated_minutes': 90},
                    {'name': 'Demand Forecasting methods', 'order': 3, 'importance_score': 3, 'estimated_minutes': 45},
                    {'name': 'Theory of Supply and Elasticity of Supply', 'order': 4, 'importance_score': 4, 'estimated_minutes': 60}
                ]
            },
            {
                'name': 'Theory of Production and Cost',
                'order': 3,
                'weightage': 15,
                'estimated_hours': 8.0,
                'topics': [
                    {'name': 'Laws of Production (Short run vs Long run)', 'order': 1, 'importance_score': 5, 'estimated_minutes': 75},
                    {'name': 'Concepts of Cost (Fixed, Variable, Opportunity)', 'order': 2, 'importance_score': 5, 'estimated_minutes': 60},
                    {'name': 'Short run and Long run Cost curves', 'order': 3, 'importance_score': 4, 'estimated_minutes': 60}
                ]
            }
        ]

        # Seeding Helper function
        def create_chapters_and_topics(subj_code, chapters_list):
            subj = subjects[subj_code]
            for c_info in chapters_list:
                topics_list = c_info.pop('topics')
                chap = Chapter.objects.create(subject=subj, **c_info)
                self.stdout.write(f"    Created Chapter: {chap.name}")
                for t_info in topics_list:
                    topic = Topic.objects.create(chapter=chap, **t_info)
                    self.stdout.write(f"      Created Topic: {topic.name}")

        create_chapters_and_topics('ACC', acc_chapters)
        create_chapters_and_topics('LAW', law_chapters)
        create_chapters_and_topics('QA', qa_chapters)
        create_chapters_and_topics('ECO', eco_chapters)

        self.stdout.write(self.style.SUCCESS("Syllabus database seeded successfully! Ready for learning command sessions."))
