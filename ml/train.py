import os
import lightgbm as lgb
import numpy as np

FEATURE_NAMES = [
    "amount",
    "term_months",
    "company_age_months",
    "monthly_revenue",
    "current_monthly_payments",
    "dti",
    "leverage",
    "bki_has_history",
    "bki_overdue_count_12m",
    "bki_max_overdue_days",
    "bki_active_loans",
    "prod_working_capital",
    "prod_equipment",
    "prod_investment",
    "prod_overdraft",
]


def generate_synthetic_credit_data(n_samples: int = 12000, random_seed: int = 42):
    """Генерация синтетических данных заемщиков МСП для обучения риск-модели."""
    np.random.seed(random_seed)

    amount = np.random.choice(np.arange(100_000, 10_000_000, 50_000), size=n_samples)
    term_months = np.random.choice([6, 12, 18, 24, 36, 48, 60], size=n_samples)
    company_age = np.random.exponential(scale=36, size=n_samples).astype(int) + 3
    revenue = np.random.lognormal(mean=14.0, sigma=0.8, size=n_samples).astype(int)
    current_payments = (revenue * np.random.uniform(0.0, 0.45, size=n_samples)).astype(int)

    # Рыночный аннуитет (22% годовых)
    r = 0.22 / 12.0
    coef = (r * ((1 + r) ** term_months)) / (((1 + r) ** term_months) - 1)
    new_payment = amount * coef

    dti = (current_payments + new_payment) / np.maximum(revenue, 1)
    leverage = amount / np.maximum(revenue * 12, 1)

    bki_has_history = np.random.choice([0, 1], size=n_samples, p=[0.1, 0.9])
    bki_overdue_count = np.random.poisson(lam=0.4, size=n_samples) * bki_has_history
    bki_max_days = np.random.choice([0, 15, 30, 60, 95], size=n_samples, p=[0.75, 0.12, 0.08, 0.03, 0.02]) * bki_has_history
    bki_active_loans = np.random.poisson(lam=1.5, size=n_samples) * bki_has_history

    prod_codes = np.random.choice([0, 1, 2, 3], size=n_samples)
    prod_wc = (prod_codes == 0).astype(int)
    prod_eq = (prod_codes == 1).astype(int)
    prod_inv = (prod_codes == 2).astype(int)
    prod_od = (prod_codes == 3).astype(int)

    X = np.column_stack([
        amount,
        term_months,
        company_age,
        revenue,
        current_payments,
        dti,
        leverage,
        bki_has_history,
        bki_overdue_count,
        bki_max_days,
        bki_active_loans,
        prod_wc,
        prod_eq,
        prod_inv,
        prod_od,
    ])

    # Логит вероятности дефолта (Ground Truth)
    logit = (
        -2.8
        + 3.2 * (dti - 0.35)
        + 1.8 * (leverage - 0.25)
        + 0.035 * bki_max_days
        + 0.6 * bki_overdue_count
        - 0.02 * np.minimum(company_age, 60)
        - 0.5 * bki_has_history
        + 0.015 * (term_months - 12)
    )
    pd_prob = 1.0 / (1.0 + np.exp(-logit))
    y = (np.random.rand(n_samples) < pd_prob).astype(int)

    return X, y


def train_and_save():
    print("Генерация обучающей выборки кредитных заявок...")
    X, y = generate_synthetic_credit_data()

    dataset = lgb.Dataset(X, label=y, feature_name=FEATURE_NAMES)

    params = {
        "objective": "binary",
        "metric": "auc",
        "boosting_type": "gbdt",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "max_depth": 5,
        "min_data_in_leaf": 40,
        "verbose": -1,
        "seed": 42,
    }

    print("Обучение градиентного бустинга LightGBM...")
    booster = lgb.train(params, dataset, num_boost_round=120)

    os.makedirs("app", exist_ok=True)
    model_path = os.path.join("app", "model.txt")
    booster.save_model(model_path)
    print(f"Модель сохранена в файл: {model_path}")


if __name__ == "__main__":
    train_and_save()