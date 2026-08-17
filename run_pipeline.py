"""Run the complete CommerceIQ Analytics pipeline."""

from src.data.pipeline import run_pipeline


if __name__ == "__main__":
    results = run_pipeline()
    validation = results["validation"]
    print(
        "CommerceIQ pipeline complete | "
        f"orders={validation['tables']['orders']['rows']:,} | "
        f"customers={validation['unique_customer_ids']:,} | "
        f"revenue=R$ {results['kpis']['total_merchandise_revenue']:,.2f} | "
        f"database={results['database_status']}"
    )
